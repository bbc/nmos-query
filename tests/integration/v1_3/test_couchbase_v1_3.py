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
# from couchbase.cluster import Cluster, PasswordAuthenticator
# import couchbase.subdocument as subdoc
from testcontainers.compose import DockerCompose
import couchbase.exceptions
from couchbase.cluster import Cluster, PasswordAuthenticator
import couchbase.subdocument as subdoc
from nmoscommon.timestamp import Timestamp
import os
import time

from tests.integration.helpers import util
from tests.integration.helpers.extended_test_case import ExtendedTestCase
from nmosquery.service import QueryService

BUCKET_NAME = 'nmos-test'
TEST_USERNAME = 'nmos-test'
TEST_PASSWORD = 'password'

AGGREGATOR_PORT = 8870

API_VERSION = 'v1.3'

DUMMY_RESOURCES = util.json_fixture("dummy_data/example.json")

IPS_TYPE_SINGULAR = {
    "flows": "flow",
    "sources": 'source',
    "nodes": 'node',
    "devices": 'device',
    "senders": 'sender',
    "receivers": 'receiver'
}

RESOURCE_TYPES = ['nodes', 'sources', 'flows', 'devices', 'senders'] # + receivers

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
    # Build bucket
    requests.post('http://{0}:{1}/pools/default/buckets'.format(host, port),
                  auth=requests.auth.HTTPBasicAuth(TEST_USERNAME, TEST_PASSWORD),
                  data={
                      'flushEnabled': 1,
                      'replicaNumber': 0,
                      'evictionPolicy': 'valueOnly',
                      'ramQuotaMB': 1024,
                      'bucketType': 'couchbase',
                      'name': BUCKET_NAME,
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


def _put_xattrs(bucket, key, xattrs, fill_timestamp_xattrs=True):
    if fill_timestamp_xattrs:
        time_now = Timestamp.get_time().to_nanosec()
        xattrs['last_updated'] = time_now
        xattrs['created_at'] = time_now
    for xkey, xvalue in xattrs.items():
        bucket.mutate_in(key, subdoc.insert(xkey, xvalue, xattr=True))


def _put_doc(bucket, key, value, xattrs, fill_timestamp_xattrs=True, ttl=12):
    bucket.insert(key, value, ttl=ttl)
    time.sleep(1)
    _put_xattrs(bucket, key, xattrs, fill_timestamp_xattrs)
    bucket.touch(key, ttl=ttl)

def _load_bucket(bucket, docs):
    for resource_type, subset in docs.items():
        for resource in subset:
            _put_doc(bucket, resource['id'], resource, {'resource_type': IPS_TYPE_SINGULAR[resource_type]}, ttl=0)


def _get_xattrs(bucket, key, xattrs):
    results = {}
    for xkey in xattrs:
        try:
            results[xkey] = bucket.lookup_in(key, subdoc.get(xkey, xattr=True))['{}'.format(xkey)]
        except couchbase.exceptions.SubdocPathNotFoundError:
            results[xkey] = None
    return results

class TestCouchbase(ExtendedTestCase):
    @classmethod
    def setUpClass(self):
        self.couch_container = DockerCompose('{}/tests/integration/'.format(os.getcwd()))
        self.couch_container.start()
        self.couch_container.wait_for('http://localhost:8091')

        host = self.couch_container.get_service_host('couchbase', 8091)
        port = self.couch_container.get_service_port('couchbase', 8091)

        _initialise_cluster(host, port, BUCKET_NAME, TEST_USERNAME, TEST_PASSWORD)

        time.sleep(5)

        self.query = QueryService()
        self.query.config['registry'] = {
            "type": "couchbase",
            "hosts": [host],
            "port": port,
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "bucket": BUCKET_NAME}
        self.query.config['priority'] = 169
        self.query.start()

        cluster = Cluster('couchbase://{}'.format(host))
        auth = PasswordAuthenticator(TEST_USERNAME, TEST_PASSWORD)
        cluster.authenticate(auth)
        self.test_bucket = cluster.open_bucket(BUCKET_NAME) # Probably not necessary to be self. Documents should be stored in advance and only reads should be via Query service
        self.test_bucket_manager = self.test_bucket.bucket_manager()

        try:
            self.test_bucket_manager.n1ql_index_create('test-bucket-primary-index', primary=True)
            # TODO: secondary indices for performance and verification
        except couchbase.exceptions.KeyExistsError:
            pass

        _load_bucket(self.test_bucket, DUMMY_RESOURCES)

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
            'http://127.0.0.1:{}/x-nmos/query/{}/flows/007ff4e5-fe72-4c4b-b858-4c5f37dff946'\
                .format(AGGREGATOR_PORT, API_VERSION)
        )

        self.assertEqual(query_response.status_code, 409)

    @classmethod
    def tearDownClass(self):
        self.couch_container.stop()
        self.query.stop()
