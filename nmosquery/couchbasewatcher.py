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

import gevent
from nmoscommon.timestamp import Timestamp

DEFAULT_START_INTERVAL = 15 # Probs should be config var, maybe accessed via registry object
POLL_RATE = 5

class CouchbaseWatcher(gevent.Greenlet):
    def __init__(self, registry, handler, logger):
        gevent.Greenlet.__init__(self)
        self.registry = registry
        self.handler = handler
        self.logger = logger
        self.events = None  # TBD if some sort of array of events makes any sense
        self.running = False

    def _run(self):
        self.logger.writeDebug('couchbasewatcher: running')
        self.running = True
        failures = 0
        secs = [0, 1, 3, 10]  # This is not used

        current_time = Timestamp.get_time().to_nanosec()
        start_time = current_time - Timestamp(sec=(DEFAULT_START_INTERVAL * 60)).to_nanosec()
        while self.running:
            updated_resources = self.registry.custom_query(
                '*',  # 'id',   # should return full documents?
                'meta().xattrs.last_updated > {}'.format(start_time),
                self.registry.buckets['registry']
            )  # use nmoscommon timestamp to determine date range


            for resource in updated_resources:
                rtype = self.registry.get_xattrs(resource['id'], ['resource_type'], self.registry.buckets['registry'])['resource_type']
                api_ver = self.registry.get_xattrs(resource['id'], ['api_version'], self.registry.buckets['registry'])['api_version']
                self.handler.process_couchbase_update(resource, {}, rtype, api_ver)

            start_time = Timestamp.get_time().to_nanosec()
            gevent.sleep(POLL_RATE)

    def stop(self):
        self.running = False
        self.kill(timeout=5)
