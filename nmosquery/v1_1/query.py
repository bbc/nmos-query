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

from nmosquery.common.query import QueryCommon, WS_PORT
from nmosquery.v1_1.querysockets import QuerySockets, QueryFilter


class Query(QueryCommon):
    def __init__(self, logger=None, registry=None):
        super(Query, self).__init__(logger, "v1.1", registry=registry)
        self.query_sockets = QuerySockets(WS_PORT, logger=self.logger)

    # see if object matches supplied arguments
    def _matches_args(self, obj, args):
        arg_checker = QueryFilter()
        return arg_checker.check_args(args, obj)
