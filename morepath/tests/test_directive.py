from .fixtures import (basic, nested, abbr, mapply_bug,
                       normalmethod, method, conflict, pkg, noconverter)
from morepath import setup
from morepath.error import (ConflictError, MountError, DirectiveError,
                            DirectiveReportError)
from morepath.view import render_html
from morepath.app import App
from morepath.converter import Converter
import morepath
from morepath.error import LinkError
import reg
import webob

import pytest
from webobtoolkit.client import Client


def setup_module(module):
    morepath.disable_implicit()


def test_basic():
    config = setup()
    config.scan(basic)
    config.commit()

    c = Client(basic.app)

    response = c.get('/foo')

    assert response.body == 'The view for model: foo'

    response = c.get('/foo/link')
    assert response.body == '/foo'


def test_basic_json():
    config = setup()
    config.scan(basic)
    config.commit()

    c = Client(basic.app)

    response = c.get('/foo/json')

    assert response.body == '{"id": "foo"}'


def test_basic_root():
    config = setup()
    config.scan(basic)
    config.commit()

    c = Client(basic.app)

    response = c.get('/')

    assert response.body == 'The root: ROOT'

    # + is to make sure we get the view, not the sub-model as
    # the model is greedy
    response = c.get('/+link')
    assert response.body == '/'


def test_nested():
    config = setup()
    config.scan(nested)
    config.commit()

    c = Client(nested.outer_app)

    response = c.get('/inner/foo')

    assert response.body == 'The view for model: foo'

    response = c.get('/inner/foo/link')
    assert response.body == '/inner/foo'


def test_abbr():
    config = setup()
    config.scan(abbr)
    config.commit()

    c = Client(abbr.app)

    response = c.get('/foo')
    assert response.body == 'Default view: foo'

    response = c.get('/foo/edit')
    assert response.body == 'Edit view: foo'


def test_scanned_normal_method():
    config = setup()
    with pytest.raises(DirectiveError):
        config.scan(normalmethod)


def test_scanned_static_method():
    config = setup()
    config.scan(method)
    config.commit()

    c = Client(method.app)

    response = c.get('/static')
    assert response.body == 'Static Method'

    root = method.Root()
    assert isinstance(root.static_method(), method.StaticMethod)


def test_scanned_class_method():
    config = setup()
    config.scan(method)
    config.commit()

    c = Client(method.app)

    response = c.get('/class')
    assert response.body == 'Class Method'

    root = method.Root()
    assert isinstance(root.class_method(), method.ClassMethod)


def test_scanned_no_converter():
    config = setup()
    config.scan(noconverter)
    with pytest.raises(DirectiveReportError):
        config.commit()


def test_scanned_conflict():
    config = setup()
    config.scan(conflict)
    with pytest.raises(ConflictError):
        config.commit()


def test_scanned_some_error():
    config = setup()
    with pytest.raises(ZeroDivisionError):
        config.scan(pkg)


def test_scanned_caller_package():
    from .fixtures import callerpkg
    callerpkg.main()

    from .fixtures.callerpkg.other import app

    c = Client(app)

    response = c.get('/')
    assert response.body == 'Hello world'


def test_imperative():
    class Foo(object):
        pass

    @reg.generic
    def target():
        pass

    app = App()

    c = setup()
    foo = Foo()
    c.configurable(app)
    c.action(app.function(target), foo)
    c.commit()

    assert target.component(lookup=app.lookup) is foo


def test_basic_imperative():
    app = morepath.App()

    class Root(object):
        def __init__(self):
            self.value = 'ROOT'

    class Model(object):
        def __init__(self, id):
            self.id = id

    def get_model(id):
        return Model(id)

    def default(self, request):
        return "The view for model: %s" % self.id

    def link(self, request):
        return request.link(self)

    def json(self, request):
        return {'id': self.id}

    def root_default(self, request):
        return "The root: %s" % self.value

    def root_link(self, request):
        return request.link(self)

    c = setup()
    c.configurable(app)
    c.action(app.path(path=''), Root)
    c.action(app.path(model=Model, path='{id}'),
             get_model)
    c.action(app.view(model=Model),
             default)
    c.action(app.view(model=Model, name='link'),
             link)
    c.action(app.view(model=Model, name='json',
                      render=morepath.render_json),
             json)
    c.action(app.view(model=Root),
             root_default)
    c.action(app.view(model=Root, name='link'),
             root_link)
    c.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == 'The view for model: foo'

    response = c.get('/foo/link')
    assert response.body == '/foo'

    response = c.get('/foo/json')
    assert response.body == '{"id": "foo"}'

    response = c.get('/')
    assert response.body == 'The root: ROOT'

    # + is to make sure we get the view, not the sub-model
    response = c.get('/+link')
    assert response.body == '/'


def test_basic_testing_config():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self):
            self.value = 'ROOT'

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='{id}')
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "The view for model: %s" % self.id

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    @app.view(model=Model, name='json', render=morepath.render_json)
    def json(self, request):
        return {'id': self.id}

    @app.view(model=Root)
    def root_default(self, request):
        return "The root: %s" % self.value

    @app.view(model=Root, name='link')
    def root_link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == 'The view for model: foo'

    response = c.get('/foo/link')
    assert response.body == '/foo'

    response = c.get('/foo/json')
    assert response.body == '{"id": "foo"}'

    response = c.get('/')
    assert response.body == 'The root: ROOT'

    # + is to make sure we get the view, not the sub-model
    response = c.get('/+link')
    assert response.body == '/'


def test_link_to_unknown_model():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self):
            self.value = 'ROOT'

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.view(model=Root)
    def root_link(self, request):
        try:
            return request.link(Model('foo'))
        except LinkError:
            return "Link error"

    @app.view(model=Root, name='default')
    def root_link_with_default(self, request):
        try:
            return request.link(Model('foo'), default='hey')
        except LinkError:
            return "Link Error"

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == 'Link error'
    response = c.get('/default')
    assert response.body == 'Link Error'


def test_link_to_none():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self):
            self.value = 'ROOT'

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.view(model=Root)
    def root_link(self, request):
        return str(request.link(None) is None)

    @app.view(model=Root, name='default')
    def root_link_with_default(self, request):
        return request.link(None, default='unknown')

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == 'True'
    response = c.get('/default')
    assert response.body == 'unknown'


def test_link_with_parameters():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self):
            self.value = 'ROOT'

    class Model(object):
        def __init__(self, id, param):
            self.id = id
            self.param = param

    @app.path(model=Model, path='{id}')
    def get_model(id, param=0):
        assert isinstance(param, int)
        return Model(id, param)

    @app.view(model=Model)
    def default(self, request):
        return "The view for model: %s %s" % (self.id, self.param)

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == 'The view for model: foo 0'

    response = c.get('/foo/link')
    assert response.body == '/foo?param=0'

    response = c.get('/foo?param=1')
    assert response.body == 'The view for model: foo 1'

    response = c.get('/foo/link?param=1')
    assert response.body == '/foo?param=1'


def test_root_link_with_parameters():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self, param=0):
            assert isinstance(param, int)
            self.param = param

    @app.view(model=Root)
    def default(self, request):
        return "The view for root: %s" % self.param

    @app.view(model=Root, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == 'The view for root: 0'

    response = c.get('/link')
    assert response.body == '/?param=0'

    response = c.get('/?param=1')
    assert response.body == 'The view for root: 1'

    response = c.get('/link?param=1')
    assert response.body == '/?param=1'


def test_implicit_variables():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='{id}')
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "The view for model: %s" % self.id

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/foo/link')
    assert response.body == '/foo'


def test_implicit_parameters():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='foo')
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "The view for model: %s" % self.id

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == 'The view for model: None'
    response = c.get('/foo?id=bar')
    assert response.body == 'The view for model: bar'
    response = c.get('/foo/link')
    assert response.body == '/foo'
    response = c.get('/foo/link?id=bar')
    assert response.body == '/foo?id=bar'


def test_implicit_parameters_default():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='foo')
    def get_model(id='default'):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "The view for model: %s" % self.id

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == 'The view for model: default'
    response = c.get('/foo?id=bar')
    assert response.body == 'The view for model: bar'
    response = c.get('/foo/link')
    assert response.body == '/foo?id=default'
    response = c.get('/foo/link?id=bar')
    assert response.body == '/foo?id=bar'


def test_convert_exception_to_internal_error():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self):
            self.value = 'ROOT'

    @app.view(model=Root)
    def default(self, request):
        1/0
        return ''

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.status == '500 Internal Server Error'


def test_simple_root():
    config = setup()
    app = morepath.App(testing_config=config)

    class Hello(object):
        pass

    hello = Hello()

    @app.path(model=Hello, path='')
    def hello_model():
        return hello

    @app.view(model=Hello)
    def hello_view(self, request):
        return 'hello'

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == 'hello'


def test_json_directive():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.json(model=Model)
    def json(self, request):
        return {'id': self.id}

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == '{"id": "foo"}'


def test_redirect():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self):
            pass

    @app.view(model=Root, render=render_html)
    def default(self, request):
        return morepath.redirect('/')

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.status == '302 Found'


def test_root_conflict():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    @app.path(path='')
    class Something(object):
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_root_conflict2():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    @app.path(path='/')
    class Something(object):
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_root_no_conflict_different_apps():
    config = setup()
    app_a = morepath.App(testing_config=config)
    app_b = morepath.App(testing_config=config)

    @app_a.path(path='')
    class Root(object):
        pass

    @app_b.path(path='')
    class Something(object):
        pass

    config.commit()


def test_model_conflict():
    config = setup()
    app = morepath.App(testing_config=config)

    class A(object):
        pass

    @app.path(model=A, path='a')
    def get_a():
        return A()

    @app.path(model=A, path='a')
    def get_a_again():
        return A()

    with pytest.raises(ConflictError):
        config.commit()


def test_model_mount_conflict():
    config = setup()
    app = morepath.App(testing_config=config)
    app2 = morepath.App(testing_config=config)

    class A(object):
        pass

    @app.path(model=A, path='a')
    def get_a():
        return A()

    @app.mount(app=app2, path='a')
    def get_mount():
        return {}

    with pytest.raises(ConflictError):
        config.commit()


def test_path_conflict():
    config = setup()
    app = morepath.App(testing_config=config)

    class A(object):
        pass

    class B(object):
        pass

    @app.path(model=A, path='a')
    def get_a():
        return A()

    @app.path(model=B, path='a')
    def get_b():
        return B()

    with pytest.raises(ConflictError):
        config.commit()


def test_path_conflict_with_variable():
    config = setup()
    app = morepath.App(testing_config=config)

    class A(object):
        pass

    class B(object):
        pass

    @app.path(model=A, path='a/{id}')
    def get_a(id):
        return A()

    @app.path(model=B, path='a/{id2}')
    def get_b(id):
        return B()

    with pytest.raises(ConflictError):
        config.commit()


def test_path_conflict_with_variable_different_converters():
    config = setup()
    app = morepath.App(testing_config=config)

    class A(object):
        pass

    class B(object):
        pass

    @app.path(model=A, path='a/{id}', converters=Converter(decode=int))
    def get_a(id):
        return A()

    @app.path(model=B, path='a/{id}')
    def get_b(id):
        return B()

    with pytest.raises(ConflictError):
        config.commit()


def test_model_no_conflict_different_apps():
    config = setup()
    app_a = morepath.App(testing_config=config)

    class A(object):
        pass

    @app_a.path(model=A, path='a')
    def get_a():
        return A()

    app_b = morepath.App(testing_config=config)

    @app_b.path(model=A, path='a')
    def get_a_again():
        return A()

    config.commit()


def test_view_conflict():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app.view(model=Model, name='a')
    def a_view(self, request):
        pass

    @app.view(model=Model, name='a')
    def a1_view(self, request):
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_view_no_conflict_different_names():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app.view(model=Model, name='a')
    def a_view(self, request):
        pass

    @app.view(model=Model, name='b')
    def b_view(self, request):
        pass

    config.commit()


def test_view_no_conflict_different_predicates():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app.view(model=Model, name='a', request_method='GET')
    def a_view(self, request):
        pass

    @app.view(model=Model, name='a', request_method='POST')
    def b_view(self, request):
        pass

    config.commit()


def test_view_no_conflict_different_apps():
    config = setup()
    app_a = morepath.App(testing_config=config)
    app_b = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app_a.view(model=Model, name='a')
    def a_view(self, request):
        pass

    @app_b.view(model=Model, name='a')
    def a1_view(self, request):
        pass

    config.commit()


def test_view_conflict_with_json():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app.view(model=Model, name='a')
    def a_view(self, request):
        pass

    @app.json(model=Model, name='a')
    def a1_view(self, request):
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_view_conflict_with_html():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app.view(model=Model, name='a')
    def a_view(self, request):
        pass

    @app.html(model=Model, name='a')
    def a1_view(self, request):
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_function_conflict():
    config = setup()
    app = morepath.App(testing_config=config)

    class A(object):
        pass

    def func(a):
        pass

    @app.function(func, A)
    def a_func(self, request):
        pass

    @app.function(func, A)
    def a1_func(self, request):
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_function_no_conflict_different_apps():
    config = setup()
    app_a = morepath.App(testing_config=config)
    app_b = morepath.App(testing_config=config)

    def func(a):
        pass

    class A(object):
        pass

    @app_a.function(func, A)
    def a_func(a):
        pass

    @app_b.function(func, A)
    def a1_func(a):
        pass

    config.commit()


def test_mount():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', testing_config=config)

    @mounted.path(path='')
    class MountedRoot(object):
        pass

    @mounted.view(model=MountedRoot)
    def root_default(self, request):
        return "The root"

    @mounted.view(model=MountedRoot, name='link')
    def root_link(self, request):
        return request.link(self)

    @app.mount(path='{id}', app=mounted)
    def get_context():
        return {}

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == 'The root'

    response = c.get('/foo/link')
    assert response.body == '/foo'


def test_mount_empty_context():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', testing_config=config)

    @mounted.path(path='')
    class MountedRoot(object):
        pass

    @mounted.view(model=MountedRoot)
    def root_default(self, request):
        return "The root"

    @mounted.view(model=MountedRoot, name='link')
    def root_link(self, request):
        return request.link(self)

    @app.mount(path='{id}', app=mounted)
    def get_context():
        pass

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == 'The root'

    response = c.get('/foo/link')
    assert response.body == '/foo'


def test_mount_context():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @mounted.path(path='')
    class MountedRoot(object):
        def __init__(self, mount_id):
            self.mount_id = mount_id

    @mounted.view(model=MountedRoot)
    def root_default(self, request):
        return "The root for mount id: %s" % self.mount_id

    @app.mount(path='{id}', app=mounted)
    def get_context(id):
        return {
            'mount_id': id
            }

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == 'The root for mount id: foo'
    response = c.get('/bar')
    assert response.body == 'The root for mount id: bar'


def test_mount_context_parameters():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @mounted.path(path='')
    class MountedRoot(object):
        def __init__(self, mount_id):
            assert isinstance(mount_id, int)
            self.mount_id = mount_id

    @mounted.view(model=MountedRoot)
    def root_default(self, request):
        return "The root for mount id: %s" % self.mount_id

    @app.mount(path='mounts', app=mounted)
    def get_context(mount_id=0):
        return {
            'mount_id': mount_id
            }

    config.commit()

    c = Client(app)

    response = c.get('/mounts?mount_id=1')
    assert response.body == 'The root for mount id: 1'
    response = c.get('/mounts')
    assert response.body == 'The root for mount id: 0'


def test_mount_context_parameters_empty_context():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @mounted.path(path='')
    class MountedRoot(object):
        # use a default parameter
        def __init__(self, mount_id='default'):
            self.mount_id = mount_id

    @mounted.view(model=MountedRoot)
    def root_default(self, request):
        return "The root for mount id: %s" % self.mount_id

    # the context does not in fact construct the context.
    # this means the parameters are instead constructed from the
    # arguments of the MountedRoot constructor, and these
    # default to 'default'
    @app.mount(path='{id}', app=mounted)
    def get_context(id):
        return {}

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == 'The root for mount id: default'
    # the URL parameter mount_id cannot interfere with the mounting
    # process
    response = c.get('/bar?mount_id=blah')
    assert response.body == 'The root for mount id: default'


def test_mount_context_standalone():
    config = setup()
    app = morepath.App('mounted', variables=['mount_id'],
                       testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self, mount_id):
            self.mount_id = mount_id

    @app.view(model=Root)
    def root_default(self, request):
        return "The root for mount id: %s" % self.mount_id

    config.commit()

    c = Client(app.mounted(mount_id='foo'))

    response = c.get('/')
    assert response.body == 'The root for mount id: foo'


def test_mount_parent_link():
    config = setup()
    app = morepath.App('app', testing_config=config)

    @app.path(path='models/{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @mounted.path(path='')
    class MountedRoot(object):
        def __init__(self, mount_id):
            self.mount_id = mount_id

    @mounted.view(model=MountedRoot)
    def root_default(self, request):
        return request.link(Model('one'), mounted=request.mounted().parent())

    @app.mount(path='{id}', app=mounted)
    def get_context(id):
        return {
            'mount_id': id
            }

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == '/models/one'


def test_mount_child_link():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @mounted.path(path='models/{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(path='')
    class Root(object):
        pass

    @app.view(model=Root)
    def app_root_default(self, request):
        return request.link(
            Model('one'),
            mounted=request.mounted().child(mounted, id='foo'))

    @app.mount(path='{id}', app=mounted)
    def get_context(id):
        return {
            'mount_id': id
            }

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == '/foo/models/one'


def test_request_view_in_mount():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    @mounted.path(path='models/{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    @mounted.view(model=Model)
    def model_default(self, request):
        return {'hey': 'Hey'}

    @app.view(model=Root)
    def root_default(self, request):
        return request.view(
            Model('x'), mounted=request.mounted().child(
                mounted, mount_id='foo'))['hey']

    @app.mount(path='{id}', app=mounted)
    def get_context(id):
        return {
            'mount_id': id
            }

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == 'Hey'


def test_run_app_with_context_without_it():
    config = setup()
    app = morepath.App('app', variables=['mount_id'], testing_config=config)
    config.commit()

    c = Client(app)
    with pytest.raises(MountError):
        c.get('/foo')


def test_mapply_bug():
    config = setup()
    config.scan(mapply_bug)
    config.commit()

    c = Client(mapply_bug.app)

    response = c.get('/')

    assert response.body == 'the root'


def test_abbr_imperative():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app.path(path='/', model=Model)
    def get_model():
        return Model()

    with app.view(model=Model) as view:
        @view()
        def default(self, request):
            return "Default view"

        @view(name='edit')
        def edit(self, request):
            return "Edit view"

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == 'Default view'

    response = c.get('/edit')
    assert response.body == 'Edit view'


def test_abbr_imperative_exception_propagated():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app.path(path='/', model=Model)
    def get_model():
        return Model()

    with pytest.raises(ZeroDivisionError):
        with app.view(model=Model) as view:
            @view()
            def default(self, request):
                return "Default view"

            1/0
