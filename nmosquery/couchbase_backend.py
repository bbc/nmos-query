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

    def _get_xattrs(self, key, xattrs):
        results = {}
        for xkey in xattrs:
            try:
                results[xkey] = self.registry.lookup_in(key, subdoc.get(xkey, xattr=True))['{}'.format(xkey)]
            except couchbase.exceptions.SubdocPathNotFoundError:
                results[xkey] = None
        return results

    def get(self, rkey, resource_type=None):
        resource_doc = self.registry.get(rkey).value

        if resource_type and self._get_xattrs(rkey, ['resource_type'])['resource_type'] !=  resource_type:
            return (409, 'Resource for key {} does not match type {}'.format(rkey, resource_type))
        return resource_doc

    def key_query(self, output, key, value):
        query = n1ql.N1QLQuery(
            'SELECT {} from `{}` WHERE {}="{}"'.format(output, self.bucket, key, value)
        )

        return [result[self.bucket] for result in self.registry.n1ql_query(query)]

    # args included for potential use of verbose mode, although this does not appear to adhere to the specification
    def get_by_resource_type(self, resource_type, args):
        rtype = resource_type[0:-1]

        return self.key_query('*', 'meta().xattrs.resource_type', rtype)
