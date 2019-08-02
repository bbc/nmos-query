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

from couchbase.cluster import Cluster, PasswordAuthenticator
import couchbase.exceptions
import couchbase.subdocument as subdoc
import couchbase.n1ql as n1ql

class CouchbaseInterface(object):
    type = 'couchbase'
    port = None

    def __init__(self, cluster_address, username, password, bucket, *args, **kwargs):
        self.cluster = Cluster('couchbase://{}'.format(','.join(cluster_address)))
        auth = PasswordAuthenticator(username, password)
        self.cluster.authenticate(auth)
        self.registry = self.cluster.open_bucket(bucket)
        self.bucket = bucket

    def get(self, rkey, resource_type=None):
        return self.registry.get(rkey).value

    def key_query(self, output, key, value):
        query = n1ql.N1QLQuery(
            'SELECT {} from `{}` WHERE {}={}'.format(output, self.bucket, key, value)
        )
        return 

    def get_by_resource_type(self, resource_type, verbose=False):
        if verbose:
            return self.key_query('*', 'resource_type', resource_type)
        else:
            return self.key_query('id', 'resource_type', resource_type)