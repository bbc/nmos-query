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
import six

class GreenletStub(object):
    pass

with mock.patch('gevent.Greenlet', GreenletStub):
    from nmosquery.changewatcher import ChangeWatcher

class TestChangeWatcher(unittest.TestCase):
    def setUp(self):
        self.handler = mock.MagicMock(name='handler')
        self.logger  = mock.MagicMock(name='logger')
        self.UUT = ChangeWatcher(mock.sentinel.host, mock.sentinel.port, self.handler, self.logger)

    @mock.patch('gevent.sleep')
    @mock.patch('nmosquery.changewatcher.EtcdEventQueue')
    def test_run(self, EtcdEventQueue, sleep):
        """The _run method is called by the greenlet as the body of the `thread', make sure it does what it's supposed to"""
        EVENTS = [ mock.sentinel.event0, mock.sentinel.event1, mock.sentinel.event2, mock.sentinel.exceptional_event ]
        EtcdEventQueue.return_value.queue = EVENTS
        def _process_response(event):
            if event == mock.sentinel.exceptional_event:
                raise Exception
            elif event in EVENTS:
                EVENTS.remove(event)
        self.handler._process_response.side_effect = _process_response
        self.handler.query_sockets.del_all_socks.side_effect = self.UUT.stop

        self.UUT._run()

        six.assertCountEqual(self, self.handler._process_response.mock_calls,
                             [mock.call(mock.sentinel.event0),
                              mock.call(mock.sentinel.event1),
                              mock.call(mock.sentinel.event2),
                              mock.call(mock.sentinel.exceptional_event),
                              mock.call(mock.sentinel.exceptional_event),
                              mock.call(mock.sentinel.exceptional_event),
                              mock.call(mock.sentinel.exceptional_event)])
        self.assertListEqual(sleep.mock_calls, [ mock.call(1), mock.call(3), mock.call(10), mock.call(10) ])
        self.handler.query_sockets.del_all_socks.assert_called_once_with()
