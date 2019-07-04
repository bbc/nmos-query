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

from gevent import monkey
monkey.patch_all()

import json # noqa E402
import signal # noqa E402
import time # noqa E402
import gevent # noqa E402
import os # noqa E402

# Handle if systemd is installed instead of newer cysystemd
try:
    from cysystemd import daemon # noqa E402
    SYSTEMD_READY = daemon.Notification.READY
except ImportError:
    from systemd import daemon # noqa E402
    SYSTEMD_READY = "READY=1"

from nmoscommon.httpserver import HttpServer # noqa E402
from nmoscommon.logger import Logger # noqa E402
from nmoscommon.mdns import MDNSEngine # noqa E402
from nmoscommon.utils import getLocalIP # noqa E402
from .api import QueryServiceAPI, QUERY_APIVERSIONS # noqa E402
from .config import config  # noqa E402

reg = {'host': 'localhost', 'port': 4001}
HOST = getLocalIP()
WS_PORT = 8870
DNS_SD_HTTP_PORT = 80
DNS_SD_HTTPS_PORT = 443
DNS_SD_NAME = 'query_' + str(HOST)
DNS_SD_TYPE = '_nmos-query._tcp'


class QueryService:

    def __init__(self, logger=None):
        self.running = False
        self.logger = Logger("regquery")
        self.logger.writeDebug('Running QueryService')
        self.config = config
        self.mdns = MDNSEngine()
        self.httpServer = HttpServer(QueryServiceAPI, WS_PORT, '0.0.0.0', api_args=[self.logger, self.config])

    def start(self):
        if self.running:
            gevent.signal(signal.SIGINT, self.sig_handler)
            gevent.signal(signal.SIGTERM, self.sig_handler)

        self.running = True
        self.mdns.start()

        self.logger.writeDebug('Running web socket server on %i' % WS_PORT)

        self.httpServer.start()

        while not self.httpServer.started.is_set():
            self.logger.writeDebug('Waiting for httpserver to start...')
            self.httpServer.started.wait()

        if self.httpServer.failed is not None:
            raise self.httpServer.failed

        self.logger.writeDebug("Running on port: {}".format(self.httpServer.port))

        priority = self.config["priority"]
        if not str(priority).isdigit():
            priority = 0

        if self.config["https_mode"] != "enabled" and self.config["enable_mdns"]:
            self.mdns.register(DNS_SD_NAME + "_http", DNS_SD_TYPE, DNS_SD_HTTP_PORT,
                               {"pri": priority,
                                "api_ver": ",".join(QUERY_APIVERSIONS),
                                "api_proto": "http"})
        if self.config["https_mode"] != "disabled" and self.config["enable_mdns"]:
            self.mdns.register(DNS_SD_NAME + "_https", DNS_SD_TYPE, DNS_SD_HTTPS_PORT,
                               {"pri": priority,
                                "api_ver": ",".join(QUERY_APIVERSIONS),
                                "api_proto": "https"})

    def run(self):
        self.running = True
        self.start()
        daemon.notify(SYSTEMD_READY)
        while self.running:
            time.sleep(1)

    def _cleanup(self):
        self.mdns.close()
        self.httpServer.stop()

    def sig_handler(self):
        self.stop()

    def stop(self):
        self.running = False
        self._cleanup()


if __name__ == '__main__':
    Service = QueryService()
    Service.run()
