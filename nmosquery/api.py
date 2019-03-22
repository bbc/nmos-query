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

from nmoscommon.webapi import WebAPI, route
from nmoscommon.nmoscommonconfig import config as _config

from .v1_0 import routes as v1_0
from .v1_1 import routes as v1_1
from .v1_2 import routes as v1_2
from .v1_3 import routes as v1_3

QUERY_APINAMESPACE = "x-nmos"
QUERY_APINAME = "query"
QUERY_APIVERSIONS = ["v1.0", "v1.1", "v1.2", "v1.3"]
if _config.get("https_mode", "disabled") == "enabled":
    QUERY_APIVERSIONS.remove("v1.0")


class QueryServiceAPI(WebAPI):

    def __init__(self, logger, config):
        super(QueryServiceAPI, self).__init__()
        self.logger = logger
        self.config = config

        self.api_v1_0 = v1_0.Routes(logger, config)
        self.add_routes(self.api_v1_0, basepath="/{}/{}/v1.0".format(QUERY_APINAMESPACE, QUERY_APINAME))

        self.api_v1_1 = v1_1.Routes(logger, config)
        self.add_routes(self.api_v1_1, basepath="/{}/{}/v1.1".format(QUERY_APINAMESPACE, QUERY_APINAME))

        self.api_v1_2 = v1_2.Routes(logger, config)
        self.add_routes(self.api_v1_2, basepath="/{}/{}/v1.2".format(QUERY_APINAMESPACE, QUERY_APINAME))

        self.api_v1_3 = v1_3.Routes(logger, config)
        self.add_routes(self.api_v1_3, basepath="/{}/{}/v1.3".format(QUERY_APINAMESPACE, QUERY_APINAME))

    @route('/')
    def __index(self):
        return (200, [QUERY_APINAMESPACE + "/"])

    @route('/' + QUERY_APINAMESPACE + '/')
    def __namespaceindex(self):
        return (200, [QUERY_APINAME + "/"])

    @route('/' + QUERY_APINAMESPACE + '/' + QUERY_APINAME + '/')
    def __nameindex(self):
        return (200, [api_version + "/" for api_version in QUERY_APIVERSIONS])
