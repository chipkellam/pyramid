import unittest
from pyramid import testing

class TestRoute(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.urldispatch import Route
        return Route

    def _makeOne(self, *arg, **kw):
        return self._getTargetClass()(*arg, **kw)

    def test_provides_IRoute(self):
        from pyramid.interfaces import IRoute
        from zope.interface.verify import verifyObject
        verifyObject(IRoute, self._makeOne('name', 'pattern'))

    def test_ctor(self):
        import types
        route = self._makeOne('name', ':path', 'factory')
        self.assertEqual(route.pattern, ':path')
        self.assertEqual(route.path, ':path')
        self.assertEqual(route.name, 'name')
        self.assertEqual(route.factory, 'factory')
        self.assertTrue(route.generate.__class__ is types.FunctionType)
        self.assertTrue(route.match.__class__ is types.FunctionType)
        self.assertEqual(route.args, ['path'])
        self.assertEqual(route.pregenerator, None)

    def test_ctor_defaults(self):
        import types
        route = self._makeOne('name', ':path')
        self.assertEqual(route.pattern, ':path')
        self.assertEqual(route.path, ':path')
        self.assertEqual(route.name, 'name')
        self.assertEqual(route.factory, None)
        self.assertTrue(route.generate.__class__ is types.FunctionType)
        self.assertTrue(route.match.__class__ is types.FunctionType)
        self.assertEqual(route.args, ['path'])
        self.assertEqual(route.pregenerator, None)

    def test_match(self):
        route = self._makeOne('name', ':path')
        self.assertEqual(route.match('/whatever'), {'path':'whatever'})

    def test_generate(self):
        route = self._makeOne('name', ':path')
        self.assertEqual(route.generate({'path':'abc'}), '/abc')

    def test_gen(self):
        request = DummyRequest({})
        route = self._makeOne('name', ':path')
        path, kw = route.gen(request, ('extra1', 'extra2'), {'path':1})
        self.assertEqual(path, '/1/extra1/extra2')
        self.assertEqual(kw, {'path':1})

    def test_gen_no_elements(self):
        request = DummyRequest({})
        route = self._makeOne('name', ':path')
        path, kw = route.gen(request, (), {'path':1})
        self.assertEqual(path, '/1')
        self.assertEqual(kw, {'path':1})

    def test_gen_no_kwargs(self):
        request = DummyRequest({})
        route = self._makeOne('name', 'foo')
        path, kw = route.gen(request, (), {})
        self.assertEqual(path, '/foo')
        self.assertEqual(kw, {})

    def test_gen_with_pregenerator(self):
        request = DummyRequest({})
        def pregenerator(request, elements, kw):
            return ('a',), {'path':2, '_app_url':'http://example.com:6543'}
        route = self._makeOne('name', ':path', pregenerator=pregenerator)
        path, kw = route.gen(request, ('extra1', 'extra2'), {'path':1})
        self.assertEqual(path, '/2/a')
        self.assertEqual(kw, {'path':2, '_app_url':'http://example.com:6543'})

class TestRouteGroup(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.urldispatch import RouteGroup
        return RouteGroup

    def _makeOne(self, *arg, **kw):
        return self._getTargetClass()(*arg, **kw)

    def _makeRoute(self, *arg, **kw):
        from pyramid.urldispatch import Route
        return Route(*arg, **kw)

    def test_add(self):
        group = self._makeOne('name')
        route0 = self._makeRoute('name', ':path')
        route1 = self._makeRoute('name', ':path/:foo')
        route2 = self._makeRoute('name', ':path/:foo/:bar')
        group.add(route0)
        group.add(route1)
        group.add(route2)

        self.assertEqual(group.name, 'name')
        self.assertEqual(len(group.routes), 3)
        self.assertEqual(len(group.sorted_routes), 3)
        self.assertEqual(group.routes[0], route0)
        self.assertEqual(group.routes[1], route1)
        self.assertEqual(group.routes[2], route2)

        entry0 = group.sorted_routes[0]
        entry1 = group.sorted_routes[1]
        entry2 = group.sorted_routes[2]
        self.assertEqual(entry0[3], route2)
        self.assertEqual(entry1[3], route1)
        self.assertEqual(entry2[3], route0)

    def test_no_match(self):
        request = DummyRequest({})
        group = self._makeOne('name')
        route0 = self._makeRoute('name', ':path')
        route1 = self._makeRoute('name', ':path/:foo')
        group.add(route0)
        group.add(route1)

        self.assertRaises(KeyError, group.gen, request, (), {})

    def test_match(self):
        request = DummyRequest({})
        group = self._makeOne('name')
        route0 = self._makeRoute('name', ':a/edit')
        route1 = self._makeRoute('name', '/p/:a/:b/:c')
        route2 = self._makeRoute('name', ':b/:c')
        group.add(route0)
        group.add(route1)
        group.add(route2)

        path, kw = group.gen(request, (), {'a':1})
        self.assertEqual(path, '/1/edit')
        self.assertEqual(kw, {'a':1})

        path, kw = group.gen(request, (), {'a':1, 'b':2, 'c':3})
        self.assertEqual(path, '/p/1/2/3')
        self.assertEqual(kw, {'a':1, 'b':2, 'c':3})

        path, kw = group.gen(request, (), {'b':2, 'c':3})
        self.assertEqual(path, '/2/3')
        self.assertEqual(kw, {'b':2, 'c':3})

    def test_match_pregenerator(self):
        request = DummyRequest({})
        def pregenerator(request, elements, kwargs):
            kwargs['a'] = 10
            return elements, kwargs
        group = self._makeOne('name')
        route0 = self._makeRoute('name', ':a/edit')
        route1 = self._makeRoute('name', '/p/:a/:b/:c',
                                 pregenerator=pregenerator)
        route2 = self._makeRoute('name', ':b/:c', pregenerator=pregenerator)
        group.add(route0)
        group.add(route1)
        group.add(route2)

        path, kw = group.gen(request, ('extra1', 'extra2'), {'a':1})
        self.assertEqual(path, '/1/edit/extra1/extra2')
        self.assertEqual(kw, {'a':1})

        path, kw = group.gen(request, ('extra1',), {'a':1, 'b':2, 'c':3})
        self.assertEqual(path, '/p/10/2/3/extra1')
        self.assertEqual(kw, {'a':10, 'b':2, 'c':3})

        path, kw = group.gen(request, (), {'b':2, 'c':3})
        self.assertEqual(path, '/p/10/2/3')
        self.assertEqual(kw, {'a':10, 'b':2, 'c':3})

    def test_match_ordering(self):
        request = DummyRequest({})
        group = self._makeOne('name')
        route0 = self._makeRoute('name', '/p/:a/:b/:c')
        route1 = self._makeRoute('name', ':a/:b/:c')
        group.add(route0)
        group.add(route1)

        path, kw = group.gen(request, (), {'a':1, 'b':2, 'c':3})
        self.assertEqual(path, '/p/1/2/3')
        self.assertEqual(kw, {'a':1, 'b':2, 'c':3})

class RoutesMapperTests(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()
        
    def _getRequest(self, **kw):
        from pyramid.threadlocal import get_current_registry
        environ = {'SERVER_NAME':'localhost',
                   'wsgi.url_scheme':'http'}
        environ.update(kw)
        request = DummyRequest(environ)
        reg = get_current_registry()
        request.registry = reg
        return request

    def _getTargetClass(self):
        from pyramid.urldispatch import RoutesMapper
        return RoutesMapper

    def _makeOne(self):
        klass = self._getTargetClass()
        return klass()

    def test_provides_IRoutesMapper(self):
        from pyramid.interfaces import IRoutesMapper
        from zope.interface.verify import verifyObject
        verifyObject(IRoutesMapper, self._makeOne())

    def test_no_route_matches(self):
        mapper = self._makeOne()
        request = self._getRequest(PATH_INFO='/')
        result = mapper(request)
        self.assertEqual(result['match'], None)
        self.assertEqual(result['route'], None)

    def test_connect_name_exists_removes_old(self):
        mapper = self._makeOne()
        mapper.connect('foo', 'archives/:action/:article')
        mapper.connect('foo', 'archives/:action/:article2')
        self.assertEqual(len(mapper.routelist), 1)
        self.assertEqual(len(mapper.routes), 1)
        self.assertEqual(mapper.routes['foo'].pattern,
                         'archives/:action/:article2')
        self.assertEqual(mapper.routelist[0].pattern,
                         'archives/:action/:article2')

    def test_connect_static(self):
        mapper = self._makeOne()
        mapper.connect('foo', 'archives/:action/:article', static=True)
        self.assertEqual(len(mapper.routelist), 0)
        self.assertEqual(len(mapper.routes), 1)
        self.assertEqual(mapper.routes['foo'].pattern,
                         'archives/:action/:article')

    def test_connect_static_overridden(self):
        mapper = self._makeOne()
        mapper.connect('foo', 'archives/:action/:article', static=True)
        self.assertEqual(len(mapper.routelist), 0)
        self.assertEqual(len(mapper.routes), 1)
        self.assertEqual(mapper.routes['foo'].pattern,
                         'archives/:action/:article')
        mapper.connect('foo', 'archives/:action/:article2')
        self.assertEqual(len(mapper.routelist), 1)
        self.assertEqual(len(mapper.routes), 1)
        self.assertEqual(mapper.routes['foo'].pattern,
                         'archives/:action/:article2')
        self.assertEqual(mapper.routelist[0].pattern,
                         'archives/:action/:article2')

    def test___call__route_matches(self):
        mapper = self._makeOne()
        mapper.connect('foo', 'archives/:action/:article')
        request = self._getRequest(PATH_INFO='/archives/action1/article1')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['foo'])
        self.assertEqual(result['match']['action'], 'action1')
        self.assertEqual(result['match']['article'], 'article1')

    def test___call__route_matches_with_predicates(self):
        mapper = self._makeOne()
        mapper.connect('foo', 'archives/:action/:article',
                       predicates=[lambda *arg: True])
        request = self._getRequest(PATH_INFO='/archives/action1/article1')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['foo'])
        self.assertEqual(result['match']['action'], 'action1')
        self.assertEqual(result['match']['article'], 'article1')

    def test___call__route_fails_to_match_with_predicates(self):
        mapper = self._makeOne()
        mapper.connect('foo', 'archives/:action/article1',
                       predicates=[lambda *arg: True, lambda *arg: False])
        mapper.connect('bar', 'archives/:action/:article')
        request = self._getRequest(PATH_INFO='/archives/action1/article1')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['bar'])
        self.assertEqual(result['match']['action'], 'action1')
        self.assertEqual(result['match']['article'], 'article1')

    def test___call__custom_predicate_gets_info(self):
        mapper = self._makeOne()
        def pred(info, request):
            self.assertEqual(info['match'], {'action':u'action1'})
            self.assertEqual(info['route'], mapper.routes['foo'])
            return True
        mapper.connect('foo', 'archives/:action/article1', predicates=[pred])
        request = self._getRequest(PATH_INFO='/archives/action1/article1')
        mapper(request)

    def test_cc_bug(self):
        # "unordered" as reported in IRC by author of
        # http://labs.creativecommons.org/2010/01/13/cc-engine-and-web-non-frameworks/
        mapper = self._makeOne()
        mapper.connect('rdf', 'licenses/:license_code/:license_version/rdf')
        mapper.connect('juri',
                       'licenses/:license_code/:license_version/:jurisdiction')

        request = self._getRequest(PATH_INFO='/licenses/1/v2/rdf')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['rdf'])
        self.assertEqual(result['match']['license_code'], '1')
        self.assertEqual(result['match']['license_version'], 'v2')

        request = self._getRequest(PATH_INFO='/licenses/1/v2/usa')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['juri'])
        self.assertEqual(result['match']['license_code'], '1')
        self.assertEqual(result['match']['license_version'], 'v2')
        self.assertEqual(result['match']['jurisdiction'], 'usa')

    def test___call__root_route_matches(self):
        mapper = self._makeOne()
        mapper.connect('root', '')
        request = self._getRequest(PATH_INFO='/')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['root'])
        self.assertEqual(result['match'], {})

    def test___call__root_route_matches2(self):
        mapper = self._makeOne()
        mapper.connect('root', '/')
        request = self._getRequest(PATH_INFO='/')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['root'])
        self.assertEqual(result['match'], {})

    def test___call__root_route_when_path_info_empty(self):
        mapper = self._makeOne()
        mapper.connect('root', '/')
        request = self._getRequest(PATH_INFO='')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['root'])
        self.assertEqual(result['match'], {})

    def test___call__root_route_when_path_info_notempty(self):
        mapper = self._makeOne()
        mapper.connect('root', '/')
        request = self._getRequest(PATH_INFO='/')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['root'])
        self.assertEqual(result['match'], {})

    def test___call__no_path_info(self):
        mapper = self._makeOne()
        mapper.connect('root', '/')
        request = self._getRequest()
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['root'])
        self.assertEqual(result['match'], {})

    def test_has_routes(self):
        mapper = self._makeOne()
        self.assertEqual(mapper.has_routes(), False)
        mapper.connect('whatever', 'archives/:action/:article')
        self.assertEqual(mapper.has_routes(), True)

    def test_get_routes(self):
        from pyramid.urldispatch import Route
        mapper = self._makeOne()
        self.assertEqual(mapper.get_routes(), [])
        mapper.connect('whatever', 'archives/:action/:article')
        routes = mapper.get_routes()
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].__class__, Route)

    def test_get_route_matches(self):
        mapper = self._makeOne()
        mapper.connect('whatever', 'archives/:action/:article')
        result = mapper.get_route('whatever')
        self.assertEqual(result.pattern, 'archives/:action/:article')

    def test_get_route_misses(self):
        mapper = self._makeOne()
        result = mapper.get_route('whatever')
        self.assertEqual(result, None)

    def test_generate(self):
        mapper = self._makeOne()
        def generator(kw):
            return 123
        route = DummyRoute(generator)
        mapper.routes['abc'] =  route
        self.assertEqual(mapper.generate('abc', {}), 123)

    def test_add_group(self):
        mapper = self._makeOne()
        group = mapper.add_group('foo')
        groups = mapper.get_groups()
        self.assertTrue('foo' in groups)
        self.assertEqual(group.name, 'foo')

    def test_connect_to_group(self):
        mapper = self._makeOne()
        group = mapper.add_group('foo')
        mapper.connect('foo', '/bar')
        mapper.connect('foo', '/baz')
        self.assertEqual(len(mapper.routes), 1)
        self.assertEqual(len(group.routes), 2)

    def test_add_group_removes_old_group(self):
        mapper = self._makeOne()
        mapper.add_group('foo')
        mapper.connect('foo', 'archives/:action')
        mapper.add_group('foo')
        mapper.connect('foo', 'archives/:action/:article2')
        group = mapper.get_group('foo')
        self.assertEqual(len(mapper.routelist), 1)
        self.assertEqual(len(mapper.routes), 1)
        self.assertEqual(len(mapper.groups), 1)
        self.assertEqual(len(group.routes), 1)
        self.assertEqual(group.routes[0].pattern,
                         'archives/:action/:article2')
        self.assertEqual(mapper.routelist[0].pattern,
                         'archives/:action/:article2')

    def test_add_group_removes_old_route(self):
        mapper = self._makeOne()
        mapper.connect('foo', 'archives/:action')
        mapper.add_group('foo')
        mapper.connect('foo', 'archives/:action/:article2')
        group = mapper.get_group('foo')
        self.assertEqual(len(mapper.routelist), 1)
        self.assertEqual(len(mapper.routes), 1)
        self.assertEqual(len(mapper.groups), 1)
        self.assertEqual(len(group.routes), 1)
        self.assertEqual(group.routes[0].pattern,
                         'archives/:action/:article2')
        self.assertEqual(mapper.routelist[0].pattern,
                         'archives/:action/:article2')

class TestCompileRoute(unittest.TestCase):
    def _callFUT(self, pattern):
        from pyramid.urldispatch import _compile_route
        return _compile_route(pattern)

    def test_no_star(self):
        matcher, generator, args = self._callFUT('/foo/:baz/biz/:buz/bar')
        self.assertEqual(matcher('/foo/baz/biz/buz/bar'),
                         {'baz':'baz', 'buz':'buz'})
        self.assertEqual(matcher('foo/baz/biz/buz/bar'), None)
        self.assertEqual(generator({'baz':1, 'buz':2}), '/foo/1/biz/2/bar')
        self.assertEqual(args, ['baz', 'buz'])

    def test_with_star(self):
        matcher, generator, args = self._callFUT(
            '/foo/:baz/biz/:buz/bar*traverse')
        self.assertEqual(matcher('/foo/baz/biz/buz/bar'),
                         {'baz':'baz', 'buz':'buz', 'traverse':()})
        self.assertEqual(matcher('/foo/baz/biz/buz/bar/everything/else/here'),
                         {'baz':'baz', 'buz':'buz',
                          'traverse':('everything', 'else', 'here')})
        self.assertEqual(matcher('foo/baz/biz/buz/bar'), None)
        self.assertEqual(generator(
            {'baz':1, 'buz':2, 'traverse':u'/a/b'}), '/foo/1/biz/2/bar/a/b')
        self.assertEqual(args, ['baz', 'buz', 'traverse'])
    
    def test_with_bracket_star(self):
        matcher, generator, args = self._callFUT(
            '/foo/{baz}/biz/{buz}/bar{remainder:.*}')
        self.assertEqual(matcher('/foo/baz/biz/buz/bar'),
                         {'baz':'baz', 'buz':'buz', 'remainder':''})
        self.assertEqual(matcher('/foo/baz/biz/buz/bar/everything/else/here'),
                         {'baz':'baz', 'buz':'buz',
                          'remainder':'/everything/else/here'})
        self.assertEqual(matcher('foo/baz/biz/buz/bar'), None)
        self.assertEqual(generator(
            {'baz':1, 'buz':2, 'remainder':'/a/b'}), '/foo/1/biz/2/bar%2Fa%2Fb')
        self.assertEqual(args, ['baz', 'buz', 'remainder'])

    def test_no_beginning_slash(self):
        matcher, generator, args = self._callFUT('foo/:baz/biz/:buz/bar')
        self.assertEqual(matcher('/foo/baz/biz/buz/bar'),
                         {'baz':'baz', 'buz':'buz'})
        self.assertEqual(matcher('foo/baz/biz/buz/bar'), None)
        self.assertEqual(generator({'baz':1, 'buz':2}), '/foo/1/biz/2/bar')
        self.assertEqual(args, ['baz', 'buz'])

    def test_url_decode_error(self):
        from pyramid.exceptions import URLDecodeError
        matcher, generator, args = self._callFUT('/:foo')
        self.assertRaises(URLDecodeError, matcher, '/%FF%FE%8B%00')
    
    def test_custom_regex(self):
        matcher, generator, args = self._callFUT(
            'foo/{baz}/biz/{buz:[^/\.]+}.{bar}')
        self.assertEqual(matcher('/foo/baz/biz/buz.bar'),
                         {'baz':'baz', 'buz':'buz', 'bar':'bar'})
        self.assertEqual(matcher('foo/baz/biz/buz/bar'), None)
        self.assertEqual(generator({'baz':1, 'buz':2, 'bar': 'html'}),
                         '/foo/1/biz/2.html')
        self.assertEqual(args, ['baz', 'buz', 'bar'])

    def test_mixed_newstyle_oldstyle_pattern_defaults_to_newstyle(self):
        # pattern: '\\/foo\\/(?P<baz>abc)\\/biz\\/(?P<buz>[^/]+)\\/bar$'
        # note presence of :abc in pattern (oldstyle match)
        matcher, generator, args = self._callFUT('foo/{baz:abc}/biz/{buz}/bar')
        self.assertEqual(matcher('/foo/abc/biz/buz/bar'),
                         {'baz':'abc', 'buz':'buz'})
        self.assertEqual(generator({'baz':1, 'buz':2}), '/foo/1/biz/2/bar')
        self.assertEqual(args, ['baz', 'buz'])

    def test_custom_regex_with_embedded_squigglies(self):
        matcher, generator, args = self._callFUT('/{buz:\d{4}}')
        self.assertEqual(matcher('/2001'), {'buz':'2001'})
        self.assertEqual(matcher('/200'), None)
        self.assertEqual(generator({'buz':2001}), '/2001')
        self.assertEqual(args, ['buz'])

    def test_custom_regex_with_embedded_squigglies2(self):
        matcher, generator, args = self._callFUT('/{buz:\d{3,4}}')
        self.assertEqual(matcher('/2001'), {'buz':'2001'})
        self.assertEqual(matcher('/200'), {'buz':'200'})
        self.assertEqual(matcher('/20'), None)
        self.assertEqual(generator({'buz':2001}), '/2001')
        self.assertEqual(args, ['buz'])

    def test_custom_regex_with_embedded_squigglies3(self):
        matcher, generator, args = self._callFUT(
            '/{buz:(\d{2}|\d{4})-[a-zA-Z]{3,4}-\d{2}}')
        self.assertEqual(matcher('/2001-Nov-15'), {'buz':'2001-Nov-15'})
        self.assertEqual(matcher('/99-June-10'), {'buz':'99-June-10'})
        self.assertEqual(matcher('/2-Nov-15'), None)
        self.assertEqual(matcher('/200-Nov-15'), None)
        self.assertEqual(matcher('/2001-No-15'), None)
        self.assertEqual(generator({'buz':'2001-Nov-15'}), '/2001-Nov-15')
        self.assertEqual(generator({'buz':'99-June-10'}), '/99-June-10')
        self.assertEqual(args, ['buz'])

class TestCompileRouteMatchFunctional(unittest.TestCase):
    def matches(self, pattern, path, expected):
        from pyramid.urldispatch import _compile_route
        matcher = _compile_route(pattern)[0]
        result = matcher(path)
        self.assertEqual(result, expected)

    def generates(self, pattern, dict, result):
        from pyramid.urldispatch import _compile_route
        self.assertEqual(_compile_route(pattern)[1](dict), result)

    def test_matcher_functional(self):
        self.matches('/', '', None)
        self.matches('', '', None)
        self.matches('/', '/foo', None)
        self.matches('/foo/', '/foo', None)
        self.matches('/:x', '', None)
        self.matches('/:x', '/', None)
        self.matches('/abc/:def', '/abc/', None)
        self.matches('', '/', {})
        self.matches('/', '/', {})
        self.matches('/:x', '/a', {'x':'a'})
        self.matches('zzz/:x', '/zzz/abc', {'x':'abc'})
        self.matches('zzz/:x*traverse', '/zzz/abc', {'x':'abc', 'traverse':()})
        self.matches('zzz/:x*traverse', '/zzz/abc/def/g',
                     {'x':'abc', 'traverse':('def', 'g')})
        self.matches('*traverse', '/zzz/abc', {'traverse':('zzz', 'abc')})
        self.matches('*traverse', '/zzz/%20abc', {'traverse':('zzz', ' abc')})
        self.matches(':x', '/La%20Pe%C3%B1a', {'x':u'La Pe\xf1a'})
        self.matches('*traverse', '/La%20Pe%C3%B1a/x',
                     {'traverse':(u'La Pe\xf1a', 'x')})
        self.matches('/foo/:id.html', '/foo/bar.html', {'id':'bar'})
        self.matches('/{num:[0-9]+}/*traverse', '/555/abc/def',
                     {'num':'555', 'traverse':('abc', 'def')})
        self.matches('/{num:[0-9]*}/*traverse', '/555/abc/def',
                     {'num':'555', 'traverse':('abc', 'def')})
        
    def test_generator_functional(self):
        self.generates('', {}, '/')
        self.generates('/', {}, '/')
        self.generates('/:x', {'x':''}, '/')
        self.generates('/:x', {'x':'a'}, '/a')
        self.generates('zzz/:x', {'x':'abc'}, '/zzz/abc')
        self.generates('zzz/:x*traverse', {'x':'abc', 'traverse':''},
                       '/zzz/abc')
        self.generates('zzz/:x*traverse', {'x':'abc', 'traverse':'/def/g'},
                       '/zzz/abc/def/g')
        self.generates('/:x', {'x':unicode('/La Pe\xc3\xb1a', 'utf-8')},
                       '/%2FLa%20Pe%C3%B1a')
        self.generates('/:x*y', {'x':unicode('/La Pe\xc3\xb1a', 'utf-8'),
                                 'y':'/rest/of/path'},
                       '/%2FLa%20Pe%C3%B1a/rest/of/path')
        self.generates('*traverse', {'traverse':('a', u'La Pe\xf1a')},
                       '/a/La%20Pe%C3%B1a')
        self.generates('/foo/:id.html', {'id':'bar'}, '/foo/bar.html')

class TestDefaultsPregenerator(unittest.TestCase):
    def _callFUT(self, pregen, *elements, **kw):
        request = DummyRequest({})
        return pregen(request, elements, kw)

    def _makeOne(self, defaults, wrapped=None):
        from pyramid.urldispatch import DefaultsPregenerator
        return DefaultsPregenerator(defaults, wrapped)

    def test_defaults(self):
        pregen = self._makeOne({'foo':'bar'})
        elements, kw = self._callFUT(pregen, baz='buz')
        self.assertEqual(elements, ())
        self.assertEqual(kw, {'foo':'bar', 'baz':'buz'})

    def test_override_default(self):
        pregen = self._makeOne({'foo':'bar'})
        elements, kw = self._callFUT(pregen, foo='dummy', baz='buz')
        self.assertEqual(elements, ())
        self.assertEqual(kw, {'foo':'dummy', 'baz':'buz'})

    def test_wrapper_defaults(self):
        inner_kw = {}
        def wrapper(request, elements, kw):
            inner_kw.update(kw)
            return ('foo',), {'baz':'buz'}
        pregen = self._makeOne({'foo':'bar'}, wrapper)
        elements, kw = self._callFUT(pregen)
        self.assertEqual(elements, ('foo',))
        self.assertEqual(inner_kw, {'foo':'bar'})
        self.assertEqual(kw, {'baz':'buz'})

    def test_wrapper_override_defaults(self):
        inner_kw = {}
        def wrapper(request, elements, kw):
            inner_kw.update(kw)
            return ('foo',), {'baz':'buz'}
        pregen = self._makeOne({'foo':'bar'}, wrapper)
        elements, kw = self._callFUT(pregen, foo='dummy')
        self.assertEqual(elements, ('foo',))
        self.assertEqual(inner_kw, {'foo':'dummy'})
        self.assertEqual(kw, {'baz':'buz'})

class DummyContext(object):
    """ """
        
class DummyRequest(object):
    def __init__(self, environ):
        self.environ = environ
    
class DummyRoute(object):
    def __init__(self, generator):
        self.generate = generator
        
