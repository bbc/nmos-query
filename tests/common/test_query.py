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

import unittest
import mock

import uuid
import json
import six

from nmosquery.common.query import QueryCommon, reg
from nmosquery import version_transforms

import copy

from uuid import *

API_VERSIONS = [ "v1.0", "v1.1", "v1.2", "v1.3" ]

node_data = {
    u'id': u'c16c9fa4-e578-11e7-b326-2b6c74db16d7',
    u'description': u'Dummy node for testing',
    u'tags': {},
    u'api': {
        u'endpoints': [
            {
                u'host': u'192.168.0.23',
                u'protocol': u'http',
                u'port': 80
            }
        ],
        u'versions': [u'v1.0', u'v1.1', u'v1.2', u'v1.3']
    },
    u'interfaces': [
        {
            u'port_id': u'AA-BB-CC-DD-EE-FF',
            u'name': u'eno1',
            u'chassis_id': None
        }
    ],
    u'hostname': u'dummy.example.com',
    u'label': u'dummy.example.com',
    u'clocks': [
        {
            u'ref_type': u'internal',
            u'name': u'clk0'
        },
        {
            u'gmid': u'AA-BB-CC-FF-FE-DD-EE-FF',
            u'locked': True,
            u'name': u'clk1',
            u'traceable': True,
            u'version': u'IEEE1588-2008',
            u'ref_type': u'ptp'
        }
    ],
    u'href': u'http://192.168.0.23/',
    u'version': u'1513150539:243021544',
    u'@_apiversion': u'v1.3',
    u'services': [
        {
            u'href': u'http://192.168.0.23/x-nmos/dummy/v1.0/',
            u'type': u'urn:x-nmos:service:dummy/v1.0'
        }
    ],
    u'caps': {},
}

node_data_string = json.dumps(node_data)

flow_data = {
    u'id': u'b30ebee2-e578-11e7-a01e-ab8cee26a3ae',
    u'@_apiversion': u'v1.3',
    u'colorspace': u'BT709',
    u'components': [
        {
            u'bit_depth': 8,
            u'height': 1080,
            u'name': u'Y',
            u'width': 1920
        },
        {
            u'bit_depth': 8,
            u'height': 1080,
            u'name': u'Cb',
            u'width': 960
        },
        {
            u'bit_depth': 8,
            u'height': 1080,
            u'name': u'Cr',
            u'width': 960
        }
    ],
    u'description': u'',
    u'device_id': u'377c29f8-e579-11e7-b2c1-03c3d0721a9a',
    u'format': u'urn:x-nmos:format:video',
    u'frame_height': 1080,
    u'frame_width': 1920,
    u'grain_rate': {
        u'denominator': 1,
        u'numerator': 25
    },
    u'interlace_mode': u'progressive',
    u'label': u'',
    u'media_type': u'video/raw',
    u'parents': [],
    u'source_id': u'405d0f2e-e579-11e7-9c88-c33046845dd9',
    u'tags': {},
    u'transfer_characteristic': u'SDR',
    u'version': u'1513670741:520081182'
}

flow_data_string = json.dumps(flow_data)

flow_v1_0_data = {
    u'@_apiversion': u'v1.0',
    "description": "",
    "format": "urn:x-nmos:format:video",
    "label": "",
    "version": "1513670741:520081182",
    "parents": [],
    "source_id": "405d0f2e-e579-11e7-9c88-c33046845dd9",
    "id": "2dbd7c0c-e595-11e7-9a90-bf0d771bd593",
    "tags": {}
}

flow_v1_0_data_string = json.dumps(flow_v1_0_data)

sender_data = {
    u'@_apiversion': u'v1.3',
    u'description': u'',
    u'device_id': u'377c29f8-e579-11e7-b2c1-03c3d0721a9a',
    u'flow_id': u'b30ebee2-e578-11e7-a01e-ab8cee26a3ae',
    u'id': u'1fe66652-e590-11e7-b23a-2796ce8be661',
    u'interface_bindings': [
        u'enxb827eb7695b6'
    ],
    u'label': u'dummy.example.com RTPTx dummy',
    u'manifest_href': u'http://192.168.0.23:12394/x-ipstudio/camctrl/v1.0/sender/1fe66652-e590-11e7-b23a-2796ce8be661/sdp/',
    u'subscription': {
        u'active': True,
        u'receiver_id': None
    },
    u'tags': {},
    u'transport': u'urn:x-nmos:transport:rtp.mcast',
    u'version': u'1455208097:709538048'
}

sender_data_string = json.dumps(sender_data)

etcd_test_data = {
    "action" : "get",
    "node" : {
        "key"   : "/resource",
        "dir"   : True,
        "nodes" : [
            {
                'key' : '/resource/nodes',
                "dir" : True,
                "node" : [
                    {
                        "key": "/resource/nodes/b30ebee2-e578-11e7-a01e-ab8cee26a3ae",
                        "value": node_data_string,
                        "modifiedIndex": 361323946,
                        "createdIndex": 361323946
                    }
                ],
                "modifiedIndex": 12,
                "createdIndex": 12
            },
            {
                "key": "/resource/flows",
                "dir": True,
                "nodes" : [
                    {
                        "key": "/resource/flows/b30ebee2-e578-11e7-a01e-ab8cee26a3ae",
                        "value": flow_data_string,
                        "modifiedIndex": 370173795,
                        "createdIndex": 370173795
                    },
                    {
                        "key": "/resource/flows/2dbd7c0c-e595-11e7-9a90-bf0d771bd593",
                        "value": flow_v1_0_data_string,
                        "modifiedIndex": 370173795,
                        "createdIndex": 370173795
                    }
                ],
                "modifiedIndex": 182,
                "createdIndex": 182
            },
            {
                "key": "/resource/senders",
                "dir": True,
                "nodes": [
                    {
                        "key": "/resource/senders/1fe66652-e590-11e7-b23a-2796ce8be661",
                        "value": sender_data_string,
                        "modifiedIndex": 354465692,
                        "createdIndex": 354465692
                    }
                ],
                "modifiedIndex": 189,
                "createdIndex": 189
            }
        ],
        "modifiedIndex": 12,
        "createdIndex": 12
    }
}

etcd_test_data_string = json.dumps(etcd_test_data)

def remove_at_keys(data):
    data = copy.deepcopy(data)
    removals = [x for x in data.keys() if x.startswith("@_")]
    for key in removals:
        del data[key]

    return data

"""Generate a set of versioned versions of the resource data to compare against returns from the code"""
flow_data_versions = { v : remove_at_keys(version_transforms.convert(copy.deepcopy(flow_data), "flows", v)) for v in API_VERSIONS }
flow_v1_0_data_versions = { v : remove_at_keys(version_transforms.convert(copy.deepcopy(flow_v1_0_data), "flows", v, "v1.0")) for v in API_VERSIONS }
sender_data_versions = { v : remove_at_keys(version_transforms.convert(copy.deepcopy(sender_data), "senders", v)) for v in API_VERSIONS }

class TestQueryCommon(unittest.TestCase):

    @mock.patch('nmosquery.common.query.ChangeWatcher')
    @mock.patch('nmosquery.common.query.Logger', side_effect=lambda name, _parent : getattr(_parent, name))
    def setup(self, v, Logger, ChangeWatcher):
        """This is not setUp! It is not called automatically!"""
        self.logger = mock.MagicMock(name="Logger()")
        self.UUT = QueryCommon(logger=self.logger, api_version=v)

        ChangeWatcher.assert_called_once_with(reg['host'], reg['port'], handler=self.UUT, logger=self.logger.regquery)
        ChangeWatcher.return_value.start.assert_called_once_with()


    @mock.patch('os.getpid', return_value=23)
    @mock.patch('socket.gethostname', return_value="example.com")
    def test_gen_source_id(self, gethostname, getpid):
        """This is pretty noddy, it's almost identical to the code of the method it's testing."""
        for v in API_VERSIONS:
            self.setup(v)
            self.assertEqual(self.UUT.gen_source_id(), str(uuid.uuid3(uuid.NAMESPACE_DNS, "23example.com")))

    def test_get_data_for_path(self):
        """This is the core method used in this class, it is supposed to return data retrieved via a GET request to the underlying database."""
        for v in API_VERSIONS:
            self.setup(v)
            # path, args, (db_resp_code, db_resp_data), expected_return_value
            test_data = [
                [ "/", {}, (404, ""), None ],
                [ "/", {}, (200, json.dumps({ "potatoes" : [ "a", "list", "of", "potatoes" ] })), [] ],
                [ "/", { }, (200, etcd_test_data_string), [ sender_data_versions[v], flow_data_versions[v] ] + ([flow_v1_0_data_versions[v]] if v == "v1.0" else []) ],
                [ "/", { "query.downgrade" : "v1.0" }, (200, etcd_test_data_string), [ sender_data_versions[v], flow_data_versions[v], flow_v1_0_data_versions[v] ] ],
                [ "/flows/", { }, (404, None), None ],
                [ "/flows/", { }, (200, etcd_test_data_string), [ flow_data_versions[v] ] + ([flow_v1_0_data_versions[v]] if v == "v1.0" else []) ],
                [ "/senders/", { }, (404, None), None ],
                [ "/senders/", { }, (200, etcd_test_data_string), [ sender_data_versions[v] ] ],
                ]

            for (path, args, (code, text), expected) in test_data:
                with mock.patch('requests.request', return_value=mock.MagicMock(name='response', status_code=code, text=text)) as request:
                    r = self.UUT.get_data_for_path(path, args)
                    request.assert_called_once_with('GET', 'http://%s:%i/v2/keys/resource/?recursive=true' % (reg['host'], reg['port']), proxies={'http': ''})
                msg = ("Call to get_data_for_path({!r},{!r}) with version {} and GET request returning {!r} returned:"
                       "\n{}\n"
                       "\nwhen we expected:"
                       "{}\n")
                msg = msg.format(path, args, v, (code, text), json.dumps(r, indent=4), json.dumps(expected, indent=4))
                if r is not None:
                    six.assertCountEqual(self, r, expected, msg)
                else:
                    self.assertEqual(r, expected, msg)

    @mock.patch('nmosquery.common.querysockets.getLocalIP', return_value="192.168.0.23")
    def test_get_ws_subscribers(self, getLocalIP):
        def websocket_details(id, resource_path=""):
            return {
                "max_update_rate_ms": 100,
                "resource_path": resource_path,
                "params": {},
                "persist": False,
                "ws_href": "ws://192.168.0.23/x-nmos/query/v1.0/ws/?uid={!s}".format(id),
                "id": str(id)
                }

        # socket_id, sockets to add before testing, uuids to assign to created sockets in order, expected response
        tests = [
            [
                None,
                [],
                [],
                []
            ],
            [
                None,
                [ {}, {} ],
                [ uuid.UUID("bfdc0ede-e59d-11e7-bb51-1bf30cb6760d"), uuid.UUID("ef2a9916-e59e-11e7-b645-e37a6121621f") ],
                [ websocket_details("bfdc0ede-e59d-11e7-bb51-1bf30cb6760d"), websocket_details("ef2a9916-e59e-11e7-b645-e37a6121621f") ]
            ],
            [
                "bfdc0ede-e59d-11e7-bb51-1bf30cb6760d",
                [ {}, {} ],
                [ uuid.UUID("bfdc0ede-e59d-11e7-bb51-1bf30cb6760d"), uuid.UUID("ef2a9916-e59e-11e7-b645-e37a6121621f") ],
                websocket_details("bfdc0ede-e59d-11e7-bb51-1bf30cb6760d")
            ],
        ]

        for (socket_id, sockets, uuids, expected) in tests:
            for v in API_VERSIONS:
                self.setup(v)

                with mock.patch('uuid.uuid4', side_effect = uuids):
                    for socket in sockets:
                        self.UUT.query_sockets.add_sock(socket)
                rval = self.UUT.get_ws_subscribers(socket_id=socket_id)
                msg="""When calling get_ws_subscribers(socket_id={!r}) on version {} after adding sockets:

{}

with uuids:

{}

Got:

{}

Expected:

{}

""".format(socket_id, v, json.dumps(sockets, indent=4), json.dumps([ str(u) for u in uuids ], indent=4), json.dumps(rval, indent=4), json.dumps(expected, indent=4))
                if isinstance(rval, list):
                    six.assertCountEqual(self, rval, expected, msg=msg)
                else:
                    self.assertEqual(rval, expected, msg=msg)

    @mock.patch('nmosquery.common.querysockets.getLocalIP', return_value="192.168.0.23")
    def test_post_ws_subscribers_and_delete_ws_subscribers(self, getLocalIP):
        def websocket_details(id, resource_path="", persist=False):
            return {
                "max_update_rate_ms": 100,
                "resource_path": resource_path,
                "params": {},
                "persist": persist,
                "ws_href": "ws://192.168.0.23/x-nmos/query/v1.0/ws/?uid={!s}".format(id),
                "id": str(id)
                }

        for v in API_VERSIONS:
            self.setup(v)

            with mock.patch('uuid.uuid4', side_effect = [ uuid.UUID("bfdc0ede-e59d-11e7-bb51-1bf30cb6760d"),
                                                          uuid.UUID("ef2a9916-e59e-11e7-b645-e37a6121621f"),
                                                          uuid.UUID("38d918c6-e5a9-11e7-8095-a784b5bb5319") ] ):
                (obj, created) = self.UUT.post_ws_subscribers({ 'resource_path' : '/' })
                self.assertEqual(obj, websocket_details("bfdc0ede-e59d-11e7-bb51-1bf30cb6760d", resource_path='/'))
                self.assertTrue(created)

                (obj, created) = self.UUT.post_ws_subscribers({ 'resource_path' : '/' })
                self.assertEqual(obj, websocket_details("bfdc0ede-e59d-11e7-bb51-1bf30cb6760d", resource_path='/'))
                self.assertFalse(created)

                (obj, created) = self.UUT.post_ws_subscribers({ 'resource_path' : '/dummy/', 'persist' : True })
                self.assertEqual(obj, websocket_details("ef2a9916-e59e-11e7-b645-e37a6121621f", resource_path='/dummy/', persist=True))
                self.assertTrue(created)

                rval = self.UUT.delete_ws_subscribers("ef2a9916-e59e-11e7-b645-e37a6121621f")
                self.assertTrue(rval)

                (obj, created) = self.UUT.post_ws_subscribers({ 'resource_path' : '/dummy/' })
                self.assertEqual(obj, websocket_details("38d918c6-e5a9-11e7-8095-a784b5bb5319", resource_path='/dummy/'))
                self.assertTrue(created)
