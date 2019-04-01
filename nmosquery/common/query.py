# Copyright 2017 British Broadcasting Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from gevent import monkey; monkey.patch_all()

import json
import os
import socket
import string
import uuid
import copy

from six import string_types

import nmosquery.util as util
import requests

from nmoscommon.logger import Logger
from nmosquery import VALID_TYPES
from nmosquery.changewatcher import ChangeWatcher
from nmosquery.etcd_util import etcd_unpack
from nmosquery.grainevent import GrainEvent
from nmosquery.common.querysockets import QuerySocketsCommon, QueryFilterCommon
from nmosquery import version_transforms

reg = {'host': 'localhost', 'port': 4001}
WS_PORT = 8870


class QueryCommon(object):

    def __init__(self, logger=None, api_version="v1.0"):
        self.logger = Logger("regquery", _parent=logger)
        self.query_sockets = QuerySocketsCommon(WS_PORT, logger=self.logger)

        # there is a choice here: watch at specific top levels (if flat), or watch all data.
        # initially, watch all data - this may be less than ideal.
        self.watcher = ChangeWatcher(reg['host'], reg['port'], handler=self, logger=self.logger)
        self.watcher.start()

        self.api_version = api_version

    def _cleanup(self):
        self.watcher.stop()
        self.watcher.join(timeout=5)

    # generates a predictable UID for this process
    def gen_source_id(self):
        seed = '{}{}'.format(os.getpid(), socket.gethostname())
        uid = str(uuid.uuid3(uuid.NAMESPACE_DNS, seed))
        return uid

    # parse services and render as a dictionary
    def parse_services_dict(self, obj, url, args, verbose):
        res_type_pattern = None
        if url is not None and url != '/' and url != '':
            res_type_pattern = util.translate_resourcetypes(url)

        if 'node' in obj:
            unpacked = etcd_unpack(obj)
            nodes = self._match_nodes(unpacked, res_type_pattern, args, verbose)
            return nodes

        return []

    # extract objects of given types that also match supplied url and args
    def _match_nodes(self, obj, pattern, args, verbose):
        retval = []

        for k, v in obj.items():
            if any(rtype in k for rtype in VALID_TYPES) and isinstance(v, string_types):
                if self._matches_path(k, pattern):
                    downgrade_ver = None
                    if args and "query.downgrade" in args:
                        downgrade_ver = args["query.downgrade"]

                    # Downgrade / convert any mis-versioned objects as required
                    resource_type = util.get_resourcetypes(k).replace("/", "")
                    json_repr = None
                    if resource_type != "":
                        json_repr = json.loads(v)
                        json_repr = version_transforms.convert(copy.deepcopy(json_repr), resource_type,
                                                               self.api_version, downgrade_ver)

                    # If nothing could be downgraded, skip over the object
                    if not json_repr:
                        continue

                    node = self._summarise(json_repr)

                    if self._matches_args(node, args):
                        if verbose:
                            retval.append(node)
                        else:
                            retval.append(node['id'])

            elif type(v) is dict:
                # explore more
                retval = retval + self._match_nodes(v, pattern, args, verbose)

        return retval

    # see if href matches supplied regex
    def _matches_path(self, href, pattern):
        return pattern is None or pattern in href

    # see if object matches supplied arguments
    def _matches_args(self, obj, args):
        arg_checker = QueryFilterCommon()
        return arg_checker.check_args(args, obj)

    # summarise service in a presentable way
    def _summarise(self, json_repr):
        if not json_repr:
            return None

        removals = [x for x in json_repr.keys() if x.startswith("@_")]
        for key in removals:
            del json_repr[key]

        return json_repr

    def _process_response(self, response):
        """
        Process a response from a GET long-poll on etcd (watch).
        `response' is a dict, decoded from JSON.
        """
        self.logger.writeDebug('process response {} {}'.format(self.api_version, response))
        if response['action'] == 'set' or response['action'] == 'delete':
            unpacked = etcd_unpack(response)
            for k, v in unpacked.items():
                restype = util.get_resourcetypes(k)

                if restype in VALID_TYPES:
                    post_obj = {}
                    pre_obj = {}
                    if v:
                        post_obj = json.loads(v.get('node', '{}'))
                        pre_obj = json.loads(v.get('prevNode', '{}'))
                    if response['action'] == 'set' and pre_obj != post_obj:
                        self.do_sup(k, pre_obj, post_obj)
                    elif response['action'] == 'delete':
                        self.do_sdown(k, pre_obj, post_obj)
                else:
                    self.logger.writeError("Invalid type '{}' in response.".format(restype))

    # Queries
    # get data for supplied path
    def get_data_for_path(self, path, args):

        # Set verbosity
        verbose = (args.get('verbose', '').lower() != 'false')

        url = 'http://%s:%i/v2/keys/resource/?recursive=true' % (reg['host'], reg['port'])
        response = requests.request('GET', url, proxies={'http': ''})
        if response.status_code != 200:
            self.logger.writeError('bad status_code %i' % response.status_code)
            return None

        else:
            return self.parse_services_dict(json.loads(response.text), path, args, verbose)

    def get_ws_subscribers(self, socket_id=None):
        obj = None
        if socket_id:
            obj = self.query_sockets.get_socket(socket_id)
        else:
            obj = self.query_sockets.get_socketlist()
        return obj

    def post_ws_subscribers(self, json):
        obj, created = self.query_sockets.post_socket(json)
        return obj, created

    def delete_ws_subscribers(self, socket_id):
        res = self.query_sockets.delete_socket(socket_id)
        return res

    def do_sync(self, ws, socket):
        # HTTP GET on etcd registry at top level
        path = util.translate_resourcetypes(socket.resource_path)
        url = 'http://{}:{}/v2/keys/resource/{}?recursive=true'.format(reg['host'], reg['port'], path)

        event = GrainEvent()
        event.source_id = self.gen_source_id()
        event.topic = socket.resource_path
        event.flow_id = socket.uuid

        # TODO: could get expensive with lots of flows...
        try:
            r = requests.request('GET', url, proxies={'http': ''})
            if r.status_code not in [200, 404]:
                err = {"type": "error", "data": "{} getting resources of topic {}".format(r.status_code, path)}
                ws.send(json.dumps(err))
                return err

            obj = json.loads(r.text)
            unpacked = etcd_unpack(obj)
            nodes = self._match_nodes(unpacked, path, socket.params, verbose=True)

            for node in nodes:
                event.addGrainFromObj(pre_obj=node, post_obj=node)
            ws.send(json.dumps(event.obj()))

        except Exception as err:
            self.logger.writeError('Exception in do_sync: {}'.format(err))

    def do_sup(self, path, pre_obj, post_obj):
        self.logger.writeDebug('do_sup {} {}'.format(self.api_version, path))
        if cmp(post_obj, pre_obj) == 0:
            return
        sockets = self.query_sockets.find_socks(path=path, obj=post_obj, p_obj=pre_obj)
        event = GrainEvent()
        event.source_id = self.gen_source_id()
        event.topic = util.get_resourcetypes(path)
        for socket in sockets:
            self.logger.writeDebug('next ws ' + socket.ws_href)

            downgrade_ver = None
            if socket.params and "query.downgrade" in socket.params:
                downgrade_ver = socket.params["query.downgrade"]

            socket_post_obj = version_transforms.convert(copy.deepcopy(post_obj), event.topic.replace("/", ""),
                                                         self.api_version, downgrade_ver)
            socket_pre_obj = version_transforms.convert(copy.deepcopy(pre_obj), event.topic.replace("/", ""),
                                                        self.api_version, downgrade_ver)

            if not socket_post_obj and not socket_pre_obj:
                continue

            socket_post_obj = self._summarise(socket_post_obj)
            socket_pre_obj = self._summarise(socket_pre_obj)

            event.flow_id = socket.uuid
            event.clearGrains()
            if socket_pre_obj is None or not self._matches_args(socket_pre_obj, socket.params):
                # Didn't previously match filter, so should be returned
                event.addGrainFromObj(pre_obj=None, post_obj=socket_post_obj)
            elif socket_post_obj is None or not self._matches_args(socket_post_obj, socket.params):
                # Doesn't match filter any longer, so shouldn't be returned
                event.addGrainFromObj(pre_obj=socket_pre_obj, post_obj=None)
            else:
                event.addGrainFromObj(pre_obj=socket_pre_obj, post_obj=socket_post_obj)
            socket.notify_subscribers(event.obj())

    def do_sdown(self, path, pre_obj, post_obj):
        self.logger.writeDebug('do_sdown {} {}'.format(self.api_version, path))
        sockets = self.query_sockets.find_socks(path=path, obj=post_obj, p_obj=pre_obj)
        event = GrainEvent()
        event.source_id = self.gen_source_id()
        event.topic = util.get_resourcetypes(path)
        for socket in sockets:
            self.logger.writeDebug('next ws ' + socket.ws_href)

            downgrade_ver = None
            if socket.params and "query.downgrade" in socket.params:
                downgrade_ver = socket.params["query.downgrade"]

            socket_pre_obj = version_transforms.convert(copy.deepcopy(pre_obj), event.topic.replace("/", ""),
                                                        self.api_version, downgrade_ver)

            if not socket_pre_obj:
                continue

            socket_pre_obj = self._summarise(socket_pre_obj)

            event.flow_id = socket.uuid
            event.clearGrains()
            event.addGrainFromObj(pre_obj=socket_pre_obj, post_obj=None)

            socket.notify_subscribers(event.obj())
