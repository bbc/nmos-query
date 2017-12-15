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

class WebAPIStub(object):
    """This is used to replace the WebAPI class so that QueryServiceAPI can inherit from it.
    It implements the bare bones version of what that class needs, ie. it executes self.add_routes(self,'')
    during init. It implements add_routes."""
    def __init__(self):
        super(WebAPIStub, self).__setattr__('mock', mock.MagicMock(name='WebAPI'))
        super(WebAPIStub, self).__setattr__('routes', {})
        self.add_routes(self, '')

    def add_routes(self, cl, basepath):
        """This method checks all the methods of the class specified and its ancestors and assigns them to the "routes" dict if they have the 
        annotations added by the _route decorator (below)"""
        def getbases(cl):
            bases = list(cl.__bases__)
            for x in cl.__bases__:
                bases += getbases(x)
            return bases

        for klass in [cl.__class__,] + getbases(cl.__class__):
            for name in klass.__dict__.keys():
                value = getattr(cl, name)
                if callable(value):
                    if hasattr(value, 'route_path'):
                        self.routes[basepath + getattr(value, 'route_path')] = [ value, getattr(value, 'route_args'), getattr(value, 'route_kwargs') ]

    def __getattr__(self, name):
        return getattr(self.mock, name)

    def __setattr__(self, name, value):
        return setattr(self.mock, name, value)

def _route(path, *args, **kwargs):
    """This is used to substitute for the route decorator, and works with the above base class."""
    def annotate_function(f):
        f.route_path = path
        f.route_args = args
        f.route_kwargs = kwargs
        return f
    return annotate_function

with mock.patch('nmoscommon.webapi.WebAPI', WebAPIStub):
    with mock.patch('nmoscommon.webapi.route', side_effect=_route) as route:
        from nmosquery.api import QueryServiceAPI

class TestQueryServiceAPI(unittest.TestCase):
    @mock.patch('nmosquery.common.query.Logger')
    def setUp(self, Logger):
        Logger.side_effect = lambda name, _parent : getattr(_parent, name)
        self.logger = mock.MagicMock(name="logger")
        self.UUT = QueryServiceAPI(self.logger)

    def test_init(self):
        self.assertIn('/',              self.UUT.routes)
        self.assertEqual(self.UUT.routes['/'][1], ())
        self.assertEqual(self.UUT.routes['/'][2], {})

        self.assertIn('/x-nmos/',       self.UUT.routes)
        self.assertEqual(self.UUT.routes['/x-nmos/'][1], ())
        self.assertEqual(self.UUT.routes['/x-nmos/'][2], {})

        self.assertIn('/x-nmos/query/', self.UUT.routes)
        self.assertEqual(self.UUT.routes['/x-nmos/query/'][1], ())
        self.assertEqual(self.UUT.routes['/x-nmos/query/'][2], {})

    def test_index(self):
        self.assertEqual(self.UUT.routes['/'][0](), (200, ["x-nmos/"]))

    def test_namespaceindex(self):
        self.assertEqual(self.UUT.routes['/x-nmos/'][0](), (200, ["query/"]))

    def test_nameindex(self):
        self.assertEqual(self.UUT.routes['/x-nmos/query/'][0](), (200, ["v1.0/", "v1.1/", "v1.2/"]))



