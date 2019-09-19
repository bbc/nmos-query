# Copyright 2019 British Broadcasting Corporation
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
import requests
import json
# from couchbase.cluster import Cluster, PasswordAuthenticator
# import couchbase.subdocument as subdoc
from testcontainers.compose import DockerCompose
import couchbase.exceptions
from couchbase.cluster import Cluster, PasswordAuthenticator
import couchbase.subdocument as subdoc
from nmoscommon.timestamp import Timestamp
from nmoscommon.logger import Logger
import os
import re
import time

from tests.integration.helpers import util
from tests.integration.helpers.extended_test_case import ExtendedTestCase
from nmosquery.service import QueryService
from ws4py.client.threadedclient import WebSocketClient
from tests.helpers import doc_generator

BUCKET_NAME = 'nmos-test'
BUCKET_CONFIG = {
    'registry': 'nmos-test',
    'meta': 'nmos-meta-config'
}
TEST_USERNAME = 'nmos-test'
TEST_PASSWORD = 'password'

MAX_WS_RETRIES = 15
DEFAULT_START_INTERVAL = 15

AGGREGATOR_PORT = 8870

API_VERSION = 'v1.2'

DUMMY_RESOURCES = util.json_fixture("dummy_data/example.json")

IPS_TYPE_SINGULAR = {
    "flows": "flow",
    "sources": 'source',
    "nodes": 'node',
    "devices": 'device',
    "senders": 'sender',
    "receivers": 'receiver'
}

RESOURCE_TYPES = ['nodes', 'sources', 'flows', 'devices', 'senders', 'receivers']

def _initialise_cluster(host, port, bucket, username, password):
    # Initialize node
    requests.post('http://{0}:{1}/nodes/self/controller/settings'.format(host, port),
                  auth=('Administrator', 'password'),
                  data={
                      'path': '/opt/couchbase/var/lib/couchbase/data',
                      'index_path': '/opt/couchbase/var/lib/couchbase/data',
                      'cbas_path': '/opt/couchbase/var/lib/couchbase/data',
                  }
                  )
    # Rename node
    requests.post('http://{0}:{1}/node/controller/rename'.format(host, port),
                  auth=requests.auth.HTTPBasicAuth('Administrator', 'password'),
                  data={
                      'hostname': '127.0.0.1',
                  }
                  )
    # Setup services
    requests.post('http://{0}:{1}/node/controller/setupServices'.format(host, port),
                  auth=requests.auth.HTTPBasicAuth('Administrator', 'password'),
                  data={
                      'services': 'kv,index,n1ql,fts',
                  }
                  )
    # Setup admin username/password
    requests.post('http://{0}:{1}/settings/web'.format(host, port),
                  auth=requests.auth.HTTPBasicAuth('Administrator', 'password'),
                  data={
                      'password': TEST_PASSWORD,
                      'username': TEST_USERNAME,
                      'port': port,
                  }
                  )
    # Build registry bucket
    requests.post('http://{0}:{1}/pools/default/buckets'.format(host, port),
                  auth=requests.auth.HTTPBasicAuth(TEST_USERNAME, TEST_PASSWORD),
                  data={
                      'flushEnabled': 1,
                      'replicaNumber': 0,
                      'evictionPolicy': 'valueOnly',
                      'ramQuotaMB': 1024,
                      'bucketType': 'couchbase',
                      'name': BUCKET_CONFIG['registry'],
                  }
                  )
    # Build meta bucket
    requests.post('http://{0}:{1}/pools/default/buckets'.format(host, port),
                  auth=requests.auth.HTTPBasicAuth(TEST_USERNAME, TEST_PASSWORD),
                  data={
                      'flushEnabled': 1,
                      'replicaNumber': 0,
                      'evictionPolicy': 'valueOnly',
                      'ramQuotaMB': 128,
                      'bucketType': 'couchbase',
                      'name': BUCKET_CONFIG['meta'],
                  }
                  )
    # Set indexer mode
    requests.post('http://{0}:{1}/settings/indexes'.format(host, port),
                  auth=requests.auth.HTTPBasicAuth(TEST_USERNAME, password),
                  data={
                  'indexerThreads': 0,
                      'maxRollbackPoints': 5,
                      'memorySnapshotInterval': 200,
                      'storageMode': 'forestdb',
                  }
                  )

    time.sleep(5)


def _put_xattrs(bucket, key, specific_xattrs, fill_defaults=True, timestamp=None):
    xattrs = {}
    if fill_defaults:
        start_time = Timestamp.get_time().to_nanosec()
        xattrs['last_updated'] = timestamp if timestamp else start_time
        xattrs['created_at'] = timestamp if timestamp else start_time
        xattrs['api_version'] = API_VERSION

    for xkey, value in specific_xattrs.items():
        xattrs[xkey] = value
    for xkey, xvalue in xattrs.items():
        bucket.mutate_in(key, subdoc.insert(xkey, xvalue, xattr=True))


def _put_doc(bucket, key, value, xattrs, fill_defaults=True, ttl=12, logger=None, timestamp=None):
    if logger:
        logger.writeDebug('_put_doc: key: {}'.format(key))
    bucket.insert(key, value, ttl=ttl)
    time.sleep(1)
    _put_xattrs(bucket, key, xattrs, fill_defaults, timestamp)
    bucket.touch(key, ttl=ttl)

def _load_bucket(bucket, docs, load_time):
    for resource_type, subset in docs.items():
        for resource in subset:
            _put_doc(bucket, resource['id'], resource, {'resource_type': IPS_TYPE_SINGULAR[resource_type], 'last_updated': load_time, 'created_at': load_time}, ttl=0)


def _get_xattrs(bucket, key, xattrs):
    results = {}
    for xkey in xattrs:
        try:
            results[xkey] = bucket.lookup_in(key, subdoc.get(xkey, xattr=True))['{}'.format(xkey)]
        except couchbase.exceptions.SubdocPathNotFoundError:
            results[xkey] = None
    return results




class TestCouchbase(ExtendedTestCase):
    class TestWebsocketClient(WebSocketClient):
        def __init__(self, *args, **kargs):
            self.return_value = None
            self.logger = Logger('TestWebsocketClient')
            super().__init__(*args, **kargs)

        def received_message(self, msg):
            message = json.loads(str(msg))
            if len(message['grain']['data']) == 7:
                return
            self.return_value = message

    @classmethod
    def setUpClass(self):
        self.couch_container = DockerCompose('{}/tests/integration/'.format(os.getcwd()))
        self.couch_container.start()
        self.couch_container.wait_for('http://localhost:8091')
        self.logger = Logger('CouchbaseTest')

        host = self.couch_container.get_service_host('couchbase', 8091)
        port = self.couch_container.get_service_port('couchbase', 8091)

        _initialise_cluster(host, port, BUCKET_NAME, TEST_USERNAME, TEST_PASSWORD)

        time.sleep(5)

        cluster = Cluster('couchbase://{}'.format(host))
        auth = PasswordAuthenticator(TEST_USERNAME, TEST_PASSWORD)
        cluster.authenticate(auth)
        self.test_bucket = cluster.open_bucket(BUCKET_CONFIG['registry'])
        self.test_bucket_manager = self.test_bucket.bucket_manager()
        self.test_meta_bucket = cluster.open_bucket(BUCKET_CONFIG['meta'])
        self.test_meta_bucket_manager = self.test_meta_bucket.bucket_manager()

        try:
            self.test_bucket_manager.n1ql_index_create('test-bucket-primary-index', primary=True)
            self.test_bucket_manager.n1ql_index_create('test-bucket-update-index', fields=['meta().xattrs.lastUpdated'])
            self.test_meta_bucket_manager.n1ql_index_create('test-meta-bucket-primary-index', primary=True)
            self.test_meta_bucket_manager.n1ql_index_create('test-meta-bucket-update-index', fields=['meta().xattrs.lastUpdated'])
            # TODO: secondary indices for performance and verification
        except couchbase.exceptions.KeyExistsError:
            self.logger.writeError('setup: Failed to create couchbase indices - at least one index already exists')
            pass

        self.load_time = Timestamp.get_time().to_nanosec() - Timestamp(sec=(DEFAULT_START_INTERVAL * 60 * 10)).to_nanosec()
        _load_bucket(self.test_bucket, DUMMY_RESOURCES, self.load_time)
        time.sleep(DEFAULT_START_INTERVAL)  # TODO: Remove?
        
        self.query = QueryService()
        self.query.config['registry'] = {
            "type": "couchbase",
            "hosts": [host],
            "port": port,
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "buckets": BUCKET_CONFIG
        }
        self.query.config['priority'] = 169
        self.query.start()

    def test_nodes(self):
        expected = [
            {u"href": "http://127.0.0.1:1234/path",
             u"id": u"efee1ab5-85f1-4ae3-b5d5-3ccc79ae76af", u"label": u"test_node", "services": []},
            {u"href": "http://192.168.100.100:12345/",
             u"id": u"007ff4e5-fe72-4c4b-b858-4c5f37dff946", u"label": u"hostname.example.com", "services": [{"type": "urn:x-nmos-opensourceprivatenamespace:service:pipelinemanager/v1.0"}]},
            {u"href": u"http://127.0.0.1:1234/path",
             u"id": u"90461aaa-a45a-48f0-ba2e-de51b45ce4ce", u"label": u"test_node", "services": [{"type": "urn:x-nmos-opensourceprivatenamespace:service:mdnsbridge/v1.0"}]}
        ]

        query_response = requests.get(
            'http://127.0.0.1:{}/x-nmos/query/{}/nodes/'.format(AGGREGATOR_PORT, API_VERSION),
        )

        self.assertListOfDictsEqual(query_response.json(),  expected, 'id')

    def test_get_node(self):
        expected = {u"href": "http://192.168.100.100:12345/",
                    u"id": u"007ff4e5-fe72-4c4b-b858-4c5f37dff946", u"label": u"hostname.example.com",
                    "services": [{"type": "urn:x-nmos-opensourceprivatenamespace:service:pipelinemanager/v1.0"}]}

        query_response = requests.get(
            'http://127.0.0.1:{}/x-nmos/query/{}/nodes/007ff4e5-fe72-4c4b-b858-4c5f37dff946'\
                .format(AGGREGATOR_PORT, API_VERSION)
        )

        self.assertDictEqual(query_response.json(), expected)

    def test_get_all_types(self):
        for rtype in RESOURCE_TYPES:
            expected = DUMMY_RESOURCES[rtype]

            query_response = requests.get(
                'http://127.0.0.1:{}/x-nmos/query/{}/{}/'.format(
                    AGGREGATOR_PORT, API_VERSION, rtype
                )
            )

            self.assertListOfDictsEqual(query_response.json(), expected, 'id', message='Testing {} resource type'.format(IPS_TYPE_SINGULAR[rtype]))

    def test_get_wrong_type(self):
        expected = {u"href": "http://192.168.100.100:12345/",
                    u"id": u"007ff4e5-fe72-4c4b-b858-4c5f37dff946", u"label": u"hostname.example.com",
                    "services": [{"type": "urn:x-nmos-opensourceprivatenamespace:service:pipelinemanager/v1.0"}]}

        query_response = requests.get(
            'http://127.0.0.1:{}/x-nmos/query/{}/flows/007ff4e5-fe72-4c4b-b858-4c5f37dff946'
            .format(AGGREGATOR_PORT, API_VERSION)
        )

        self.assertEqual(query_response.status_code, 409)

    def test_websocket_create(self):
        request_payload = {
            'max_update_rate_ms': 100,
            'persist': True,
            'resource_path': '/nodes',
            'params': {}
        }
        
        new_node = doc_generator.generate_node()

        port = requests.post(
            'http://127.0.0.1:{}/x-nmos/query/{}/subscriptions'.format(AGGREGATOR_PORT, API_VERSION),
            json=request_payload
        )

        ws = self.TestWebsocketClient('ws://127.0.0.1:{}/x-nmos'.format(AGGREGATOR_PORT) + port.json()['ws_href'].split('x-nmos')[1])
        ws.connect()

        create_timestamp = Timestamp.get_time().to_nanosec()

        _put_doc(self.test_bucket, new_node['id'], new_node, {'resource_type': 'node'}, ttl=0, logger=self.logger, timestamp=create_timestamp)

        xx = 0

        while (not ws.return_value or len(ws.return_value) == 0) and xx < MAX_WS_RETRIES:
            time.sleep(1)
            xx += 1
            print('waiting: {}'.format(xx))

        if xx == MAX_WS_RETRIES:
            self.fail(msg='Max wait exceeded by webxocket client')

        expected_grain = {
            'grain_type': 'event',
            'source_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
            'flow_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
            'origin_timestamp': '0:0',  # verify timestamp
            'sync_timestamp': '0:0',  # verify timestamp
            'creation_timestamp': '0:0',  # verify timestamp
            'rate': {'numerator': 0, 'denominator': 1},
            'duration': {'numerator': 0, 'denominator': 1},
            'grain': []
        }


        self.assertEqual(len(ws.return_value['grain']['data']), 1)
        self.assertListEqual(sorted(list(ws.return_value.keys())), sorted(['grain_type', 'source_id', 'flow_id', 'origin_timestamp',
                                                        'sync_timestamp', 'creation_timestamp', 'rate', 'duration',
                                                        'grain']))
        self.assertDictEqual(ws.return_value['grain']['data'][0]['post'], new_node)
        self.assertDictsMostlyEqual(ws.return_value, expected_grain, fuzzy_keys=['source_id', 'flow_id'], ignored_keys=['grain'])

        ws.close()

    def test_websocket_delete(self):
        request_payload = {
            'max_update_rate_ms': 100,
            'persist': True,
            'resource_path': '/nodes',
            'params': {}
        }
        
        new_node = doc_generator.generate_node()

        port = requests.post(
            'http://127.0.0.1:{}/x-nmos/query/{}/subscriptions'.format(AGGREGATOR_PORT, API_VERSION),
            json=request_payload
        )

        ws = self.TestWebsocketClient('ws://127.0.0.1:{}/x-nmos'.format(AGGREGATOR_PORT) + port.json()['ws_href'].split('x-nmos')[1])
        ws.connect()

        create_timestamp = Timestamp.get_time().to_nanosec()

        _put_doc(self.test_meta_bucket, new_node['id'], new_node, {'resource_type': 'node'}, ttl=0, logger=self.logger, timestamp=create_timestamp)

        xx = 0

        while (not ws.return_value or len(ws.return_value) == 0) and xx < MAX_WS_RETRIES:
            time.sleep(1)
            xx += 1
            print('waiting: {}'.format(xx))

        if xx == MAX_WS_RETRIES:
            self.fail(msg='Max wait exceeded by webxocket client')

        expected_grain = {
            'grain_type': 'event',
            'source_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
            'flow_id': re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
            'origin_timestamp': '0:0',  # verify timestamp
            'sync_timestamp': '0:0',  # verify timestamp
            'creation_timestamp': '0:0',  # verify timestamp
            'rate': {'numerator': 0, 'denominator': 1},
            'duration': {'numerator': 0, 'denominator': 1},
            'grain': []
        }


        self.assertEqual(len(ws.return_value['grain']['data']), 1)
        self.assertListEqual(sorted(list(ws.return_value.keys())), sorted(['grain_type', 'source_id', 'flow_id', 'origin_timestamp',
                                                        'sync_timestamp', 'creation_timestamp', 'rate', 'duration',
                                                        'grain']))
        self.assertDictEqual(ws.return_value['grain']['data'][0]['pre'], new_node)
        self.assertDictsMostlyEqual(ws.return_value, expected_grain, fuzzy_keys=['source_id', 'flow_id'], ignored_keys=['grain'])

        ws.close()

    @classmethod
    def tearDownClass(self):
        self.query.stop()
        self.couch_container.stop()
