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

import json

from functools import wraps
from socket import error as socket_error

class WebAPIStub(object):
    """This is used to replace the WebAPI class so that QueryServiceAPI can inherit from it.
    It implements the bare bones version of what that class needs, ie. it executes self.add_routes(self,'')
    during init. It implements add_routes."""
    def __init__(self):
        super(WebAPIStub, self).__setattr__('mock', mock.MagicMock(name='WebAPI'))
        super(WebAPIStub, self).__setattr__('routes', {})
        super(WebAPIStub, self).__setattr__('websockets', {})
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
                        methods = ["GET", "OPTIONS", "HEAD"]
                        if 'methods' in getattr(value, 'route_kwargs'):
                            methods = getattr(value, 'route_kwargs')['methods']
                        if basepath + getattr(value, 'route_path') not in self.routes:
                            self.routes[basepath + getattr(value, 'route_path')] = {}
                        for method in methods:
                            self.routes[basepath + getattr(value, 'route_path')][method] = [ value, getattr(value, 'route_args'), getattr(value, 'route_kwargs') ]
                    if hasattr(value, 'ws_path'):
                        methods = ["GET", "OPTIONS", "HEAD"]
                        ws_mock = mock.MagicMock(name='ws_for_' + basepath + getattr(value, 'ws_path'), side_effect=value)
                        @wraps(value)
                        def _call_though_mock(*args, **kwargs):
                            return ws_mock(*args, **kwargs)
                        self.websockets[basepath + getattr(value, 'ws_path')] = [ cl.on_websocket_connect(_call_though_mock), ws_mock, getattr(value, 'ws_args'), getattr(value, 'ws_kwargs') ]

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

def _on_json(path, *args, **kwargs):
    """This is used to substitute for the on_json decorator, and works with the above base class."""
    def annotate_function(f):
        f.ws_path = path
        f.ws_args = args
        f.ws_kwargs = kwargs
        return f
    return annotate_function

with mock.patch('nmoscommon.webapi.WebAPI', WebAPIStub):
    with mock.patch('nmoscommon.webapi.route', side_effect=_route) as route:
        with mock.patch('nmoscommon.webapi.on_json', side_effect=_on_json) as on_json:
            from nmosquery.api import QueryServiceAPI
            from nmosquery import VALID_TYPES

class AbortException(Exception):
    pass

API_VERSIONS = ['v1.0', 'v1.1', 'v1.2', 'v1.3']

class TestQueryServiceAPI(unittest.TestCase):
    @mock.patch('nmosquery.common.routes.QueryCommon')
    @mock.patch('nmosquery.v1_0.routes.Query')
    @mock.patch('nmosquery.v1_1.routes.Query')
    @mock.patch('nmosquery.v1_2.routes.Query')
    @mock.patch('nmosquery.v1_3.routes.Query')
    def setUp(self, v1_3Query, v1_2Query, v1_1Query, v1_0Query, QueryCommon):
        self.queries = {'v1.0' : v1_0Query.return_value,
                        'v1.1' : v1_1Query.return_value,
                        'v1.2' : v1_2Query.return_value,
                        'v1.3' : v1_3Query.return_value,}
        self.logger = mock.MagicMock(name="logger")
        self.config = mock.MagicMock(dict)
        self.UUT = QueryServiceAPI(self.logger, self.config)

    def test_init(self):
        self.assertIn('/',              self.UUT.routes)
        self.assertEqual(self.UUT.routes['/']['GET'][1], ())
        self.assertEqual(self.UUT.routes['/']['GET'][2], {})

        self.assertIn('/x-nmos/',       self.UUT.routes)
        self.assertEqual(self.UUT.routes['/x-nmos/']['GET'][1], ())
        self.assertEqual(self.UUT.routes['/x-nmos/']['GET'][2], {})

        self.assertIn('/x-nmos/query/', self.UUT.routes)
        self.assertEqual(self.UUT.routes['/x-nmos/query/']['GET'][1], ())
        self.assertEqual(self.UUT.routes['/x-nmos/query/']['GET'][2], {})

    def test_index(self):
        self.assertEqual(self.UUT.routes['/']['GET'][0](), (200, ["x-nmos/"]))

    def test_namespaceindex(self):
        self.assertEqual(self.UUT.routes['/x-nmos/']['GET'][0](), (200, ["query/"]))

    def test_nameindex(self):
        self.assertEqual(self.UUT.routes['/x-nmos/query/']['GET'][0](), (200, [api_version + "/" for api_version in API_VERSIONS]))

    # These additional methods test out routes added by the common.routes.RoutesCommon class
    def test_versionindex(self):
        for v in API_VERSIONS:
            self.assertEqual(self.UUT.routes['/x-nmos/query/' + v + '/']['GET'][0](), (200, ["subscriptions/"] + [ ips_type + '/' for ips_type in VALID_TYPES ]))

    def assert_route_returns_value(self, v, path, args, expected, request, method='GET'):
        self.assertIn(path, self.UUT.routes)
        self.assertIn(method, self.UUT.routes[path])
        self.assertGreater(len(self.UUT.routes), 0)
        rval = self.UUT.routes[path][method][0](*args)
        self.assertEqual(rval, expected, msg="""
When checking the result of a """ + method + """ with path """ + path + """ the result is not as expected:

Got:

""" + repr(rval) + """

Expected:

""" + repr(expected) + """
""")

    @mock.patch('nmosquery.common.routes.abort', side_effect=AbortException)
    @mock.patch('nmosquery.common.routes.request')
    def test_ips_type(self, request, abort):
        """This method should call through to the relevent query"""
        for v in API_VERSIONS:
            for t in VALID_TYPES:
                self.queries[v].get_data_for_path.reset_mock()
                self.queries[v].get_data_for_path.return_value = mock.DEFAULT
                self.assert_route_returns_value(v, '/x-nmos/query/' + v + '/<ips_type>/', [t,], (200, self.queries[v].get_data_for_path.return_value), request)
                self.queries[v].get_data_for_path.assert_called_once_with('/' + t, request.args)

                self.queries[v].get_data_for_path.reset_mock()
                self.queries[v].get_data_for_path.return_value = None
                self.assert_route_returns_value(v, '/x-nmos/query/' + v + '/<ips_type>/', [t,], (200, []), request)
                self.queries[v].get_data_for_path.assert_called_once_with('/' + t, request.args)

            if True:
                abort.reset_mock()
                with self.assertRaises(AbortException):
                    self.UUT.routes['/x-nmos/query/' + v + '/<ips_type>/']['GET'][0]('potato')
                abort.assert_called_once_with(404)


    @mock.patch('nmosquery.common.routes.abort', side_effect=AbortException)
    @mock.patch('nmosquery.common.routes.request')
    def test_el_id(self, request, abort):
        """This method should call through to the relevent query"""
        EL_ID = "EL_ID000"
        for v in API_VERSIONS:
            for t in VALID_TYPES:
                self.queries[v].get_data_for_path.reset_mock()
                self.queries[v].get_data_for_path.return_value = mock.DEFAULT
                self.assert_route_returns_value(v, '/x-nmos/query/' + v + '/<ips_type>/<el_id>/', [t, EL_ID,], (200, self.queries[v].get_data_for_path.return_value), request)
                self.queries[v].get_data_for_path.assert_called_once_with('/' + t + '/' + EL_ID, request.args)

                self.queries[v].get_data_for_path.reset_mock()
                self.queries[v].get_data_for_path.return_value = None
                self.assert_route_returns_value(v, '/x-nmos/query/' + v + '/<ips_type>/<el_id>/', [t, EL_ID,], (404,''), request)
                self.queries[v].get_data_for_path.assert_called_once_with('/' + t + '/' + EL_ID, request.args)

                self.queries[v].get_data_for_path.reset_mock()
                self.queries[v].get_data_for_path.return_value = [ mock.sentinel.query_data0, mock.sentinel.query_data1 ]
                self.assert_route_returns_value(v, '/x-nmos/query/' + v + '/<ips_type>/<el_id>/', [t, EL_ID,], (200, mock.sentinel.query_data0), request)
                self.queries[v].get_data_for_path.assert_called_once_with('/' + t + '/' + EL_ID, request.args)

            if True: # Done to indent this block
                t = "nmos-potato"
                abort.reset_mock()
                with self.assertRaises(AbortException) as e:
                    self.UUT.routes['/x-nmos/query/' + v + '/<ips_type>/<el_id>/']['GET'][0](t, EL_ID)
                abort.assert_called_once_with(404)

    @mock.patch('nmosquery.common.routes.abort', side_effect=AbortException)
    @mock.patch('nmosquery.common.routes.request')
    def test_subscriptions_post(self, request, abort):
        request.method = "POST"
        data = { 'foo' : 'bar', 'baz' : [ 'boop', ] }

        for v in API_VERSIONS:
            request.get_data = mock.MagicMock(return_value=json.dumps(data))
            self.queries[v].post_ws_subscribers.reset_mock()
            self.queries[v].post_ws_subscribers.return_value = (mock.sentinel.obj, True)
            self.assert_route_returns_value(v, '/x-nmos/query/' + v + '/subscriptions', [], (201, mock.sentinel.obj), request, method="POST")
            self.queries[v].post_ws_subscribers.assert_called_once_with(data)

            request.get_data = mock.MagicMock(return_value=json.dumps(data))
            self.queries[v].post_ws_subscribers.reset_mock()
            self.queries[v].post_ws_subscribers.return_value = (mock.sentinel.obj, False)
            self.assert_route_returns_value(v, '/x-nmos/query/' + v + '/subscriptions', [], (200, mock.sentinel.obj), request, method="POST")
            self.queries[v].post_ws_subscribers.assert_called_once_with(data)

            request.get_data = mock.MagicMock(return_value="{")
            abort.reset_mock()
            with self.assertRaises(AbortException):
                self.UUT.routes['/x-nmos/query/' + v + '/subscriptions']['POST'][0]()
            abort.assert_called_once_with(400, mock.ANY)

    @mock.patch('nmosquery.common.routes.abort', side_effect=AbortException)
    @mock.patch('nmosquery.common.routes.request')
    def test_subscriptions_get(self, request, abort):
        data = { 'foo' : 'bar', 'baz' : [ 'boop', ] }

        for v in API_VERSIONS:
            request.get_data = json.dumps(data)
            self.queries[v].get_ws_subscribers.reset_mock()
            self.queries[v].get_ws_subscribers.return_value = mock.sentinel.obj
            self.assert_route_returns_value(v, '/x-nmos/query/' + v + '/subscriptions/', [], (200, mock.sentinel.obj), request)
            self.queries[v].get_ws_subscribers.assert_called_once_with()

    @mock.patch('nmosquery.common.routes.abort', side_effect=AbortException)
    @mock.patch('nmosquery.common.routes.request')
    def test_subscriptions_id(self, request, abort):
        ID = "subscrid"

        for v in API_VERSIONS:
            """GET when object exists"""
            request.method = "GET"
            self.queries[v].get_ws_subscribers.reset_mock()
            self.queries[v].get_ws_subscribers.return_value = mock.sentinel.obj
            self.queries[v].delete_ws_subscribers.reset_mock()
            self.assert_route_returns_value(v, '/x-nmos/query/' + v + '/subscriptions/<socket_id>', [ID,], (200, mock.sentinel.obj), request)
            self.queries[v].get_ws_subscribers.assert_called_once_with(ID)
            self.queries[v].delete_ws_subscribers.assert_not_called()

            """GET when object doens't exist"""
            request.method = "GET"
            self.queries[v].get_ws_subscribers.reset_mock()
            self.queries[v].get_ws_subscribers.return_value = None
            self.queries[v].delete_ws_subscribers.reset_mock()
            abort.reset_mock()
            with self.assertRaises(AbortException):
                self.UUT.routes['/x-nmos/query/' + v + '/subscriptions/<socket_id>']['GET'][0](ID)
            abort.assert_called_once_with(404, mock.ANY)
            self.queries[v].get_ws_subscribers.assert_called_once_with(ID)
            self.queries[v].delete_ws_subscribers.assert_not_called()

            """DELETE when object exists and can be deleted"""
            request.method = "DELETE"
            self.queries[v].get_ws_subscribers.reset_mock()
            self.queries[v].get_ws_subscribers.return_value = mock.sentinel.obj
            self.queries[v].delete_ws_subscribers.reset_mock()
            self.queries[v].delete_ws_subscribers.return_value = True
            self.assert_route_returns_value(v, '/x-nmos/query/' + v + '/subscriptions/<socket_id>', [ID,], (204, None), request, method="DELETE")
            self.queries[v].get_ws_subscribers.assert_called_once_with(ID)
            self.queries[v].delete_ws_subscribers.assert_called_once_with(ID)

            """DELETE when object exists and cannot be deleted"""
            request.method = "DELETE"
            self.queries[v].get_ws_subscribers.reset_mock()
            self.queries[v].get_ws_subscribers.return_value = mock.sentinel.obj
            self.queries[v].delete_ws_subscribers.reset_mock()
            self.queries[v].delete_ws_subscribers.return_value = False
            abort.reset_mock()
            with self.assertRaises(AbortException):
                self.UUT.routes['/x-nmos/query/' + v + '/subscriptions/<socket_id>']['DELETE'][0](ID)
            abort.assert_called_once_with(403, mock.ANY)
            self.queries[v].get_ws_subscribers.assert_called_once_with(ID)
            self.queries[v].delete_ws_subscribers.assert_called_once_with(ID)

            """DELETE when object doesn't exist."""
            request.method = "DELETE"
            self.queries[v].get_ws_subscribers.reset_mock()
            self.queries[v].get_ws_subscribers.return_value = None
            self.queries[v].delete_ws_subscribers.reset_mock()
            self.assert_route_returns_value(v, '/x-nmos/query/' + v + '/subscriptions/<socket_id>', [ID,], (204, None), request, method="DELETE")
            self.queries[v].get_ws_subscribers.assert_called_once_with(ID)
            self.queries[v].delete_ws_subscribers.assert_not_called()

    def assert_ws_handler_operates_as_expected(self, v, has_socket=True, raise_exception=Exception, persist=False, vanishing_act=False):
        args = { 'path' : 'tmp/potato/',
                'arg0'  : 'val0',
                'arg1'  : 'val1',
                'uid'   : 'cf670c6e-e40d-11e7-9bcb-9f967b40ad60' }
        msg = { 'foo' : 'bar', 'baz' : ['boop', ] }

        def _parse_env_str(args):
            d = dict(y.split('=') for y in args.split('&'))
            p = d.get('path', '')
            del d['path']
            return (p,d)

        self.UUT.websockets['/x-nmos/query/' + v + '/ws/'][1].reset_mock()
        self.queries[v].query_sockets.get_sock.reset_mock()
        self.queries[v].do_sync.reset_mock()

        self.queries[v].query_sockets.parse_env_str.side_effect = _parse_env_str
        socket = mock.MagicMock(name='socket')
        if has_socket:
            self.queries[v].query_sockets.sockets = [ socket ]
        else:
            self.queries[v].query_sockets.sockets = []

        def _get_sock(params):
            if len(self.queries[v].query_sockets.sockets) > 0 and not vanishing_act:
                return self.queries[v].query_sockets.sockets[0]
            elif len(self.queries[v].query_sockets.sockets) > 0 and vanishing_act:
                return self.queries[v].query_sockets.sockets.pop(0)
            else:
                return None

        self.queries[v].query_sockets.get_sock.side_effect = _get_sock
        socket.subscribers = []
        socket.add_subscriber.side_effect = lambda x : socket.subscribers.append(x)
        socket.persist = persist
        ws = mock.MagicMock(name="ws", environ={'QUERY_STRING' : '&'.join(('='.join((k,v)) for (k,v) in args.items()))})
        ws.receive.side_effect = [ msg, raise_exception ]

        self.UUT.websockets['/x-nmos/query/' + v + '/ws/'][0](ws)

        self.queries[v].query_sockets.get_sock.assert_called_once_with({ 'uuid' : args['uid']})

        if has_socket:
            socket.add_subscriber.assert_called_once_with(ws)
            self.queries[v].do_sync.assert_called_once_with(ws, socket)
            self.UUT.websockets['/x-nmos/query/' + v + '/ws/'][1].assert_called_once_with(ws, msg)
            if not persist:
                self.assertEqual(self.queries[v].query_sockets.sockets, [])
            else:
                self.assertEqual(self.queries[v].query_sockets.sockets, [socket, ])
        else:
            socket.add_subscriber.assert_not_called()
            self.queries[v].do_sync.assert_not_called()
            self.UUT.websockets['/x-nmos/query/' + v + '/ws/'][1].assert_not_called()
            self.assertEqual(self.queries[v].query_sockets.sockets, [])

    def test_ws__with_socket__with_msg__non_persist(self):
        """This tests that the websocket methods respond as expected when the socket exists, the message can be accessed, and the socket is not persistant"""
        for v in API_VERSIONS:
            self.assert_ws_handler_operates_as_expected(v)

    def test_ws__without_socket(self):
        """This tests that the websocket methods respond as expected when the socket cannot be created"""
        for v in API_VERSIONS:
            self.assert_ws_handler_operates_as_expected(v, has_socket=False)

    def test_ws__with_socket__with_exception(self):
        """This tests that the websocket methods respond as expected when the socket dies normally"""
        for v in API_VERSIONS:
            self.assert_ws_handler_operates_as_expected(v, raise_exception=socket_error)

    def test_ws__with_socket__with_msg__persist(self):
        """This tests that the websocket methods respond as expected when the socket exists, the message can be accessed, and the socket is persistant"""
        for v in API_VERSIONS:
            self.assert_ws_handler_operates_as_expected(v, persist=True)

    def test_ws__with_socket__which_mysteriously_disappears_during_running(self):
        """This tests that the websocket methods respond as expected when the socket exists, but then vanishes before it can be deleted. This should be handled gracefully."""
        for v in API_VERSIONS:
            self.assert_ws_handler_operates_as_expected(v, vanishing_act=True)
