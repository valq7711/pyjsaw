import os, re
from websaw import DefaultContext, DefaultApp, DAL, Cache, Field, HTTP
from websaw.core import Fixture
from websaw.core.core_events import CoreEvents, core_event_bus
from pydal.validators import CRYPT
from . import fs2json

__static_version__ = '1.0.3'

class Logged(Fixture):
    def take_on(self, ctx: 'Context'):
        if not ('user' in ctx.session and ctx.session['user']['id']):
            raise HTTP(401, body='Sorry')

class Context(DefaultContext):
    logged_in = Logged()


ctx_ = Context()

app = DefaultApp(ctx_, name=__package__)

@app.route('login', method='POST')
def login(ctx: Context):
    valid = False
    password = ctx.request.json.get('password')
    ''' JAB COMMENT OUT FOR NOW
    password_file = os.environ.get('PY4WEB_PASSWORD_FILE')
    if password and password_file and os.path.exists(password_file):
        with open(password_file, 'r') as fp:
            encrypted_password = fp.read().strip()
            valid = CRYPT()(password)[0] == encrypted_password
    if valid:
    '''    
    ctx.session['user'] = dict(id=1)
    return dict(user=valid, app='v3p')

@app.route('logout', method='POST')
def logout(ctx: Context):
    ctx.session['user'] = None
    return dict()

@app.route('index')
@app.use('index.html')
def index(ctx: Context):
    return dict(web23py='web3py',
                title = 'Vue3pyj',
                static_version ='',
                app_root = ctx.get('base_url')
    )

APPS_FOLDER = os.environ['WEBSAW_APPS_FOLDER']

@app.route('app_list')
def app_list(ctx: Context):
    print('Inside app liest')
    return dict(app_list = [app for app in next(os.walk(APPS_FOLDER))[1] if not app.startswith('__')])

@app.route('get_fs/<w23p_app>')
def get_fs(ctx: Context, w23p_app = None):
    print('INside get fs')
    app_rex  = re.compile('^[a-z_][a-z_0-9]*$', flags = re.I)
    if not (w23p_app and app_rex.match(w23p_app)):
        return dict()

    file_mask = re.compile('(.+?(?!\.min))\.(js|py|css|html|vuepy|pyj)$', flags= re.I)
    dir_list = {
        'controllers':'*',
        'static': {
            'js': {},
            'css': '*',
            'components': '*',
        },
        'modules':'*',
        'models':'*',
        'views':'*',
        'templates':'*',
        'vuepy':'*',
        #'RapydScript':{'src':'*', 'test':'*'},
        #'RapydScript':'*',
    }
    app_folder = os.path.join(APPS_FOLDER, w23p_app)
    ret = fs2json.dir_to_fs(app_folder, dir_list, file_mask)
    return ret

@app.route('create_dir', method = 'POST')
def create_dir(ctx: Context):
    w23p_app = ctx.request.json.get('w23p_app')
    dir_path = ctx.request.json.get('dir_path')
    if os.path.isabs(dir_path):
        dir_path = os.path.relpath(dir_path, '/')
    dir_path = os.path.join(APPS_FOLDER, w23p_app, dir_path)
    os.mkdir(dir_path)
    return dict(new_dir = dir_path)

@app.route('write_file', method = 'POST')
def write_file(ctx: Context):
    fdata = { k:ctx.request.forms.get(k) for k in ctx.request.forms}
    fdata['content'] =  ctx.request.files['content'].file
    w23p_app = fdata.get('w23p_app', None)
    app_folder = os.path.join(APPS_FOLDER, w23p_app) if w23p_app else os.path.normpath(ctx.request.folder)
    ret = fs2json.write_file(fdata, app_folder)
    return dict(ret)

@app.route('del_file', method = 'POST')
def del_file(ctx: Context):
    app_folder = os.path.dirname(__file__)
    fdata = ctx.request.json.get('fdata')
    w23p_app = fdata.get('w23p_app')
    app_folder = os.path.join(APPS_FOLDER, w23p_app) if w23p_app else os.path.normpath(app_folder)
    ret = fs2json.del_file(fdata, app_folder)
    return dict(ret)

@app.route('try_connect', method = 'GET')
def try_connect(ctx: Context):
    return dict(flash='Hi!')

@app.route('reload')
@app.route('reload/<name>')
def reload(ctx: Context, name = None):
    """reloads installed apps"""
    name_wrapped = [name] if name is not None else []
    core_event_bus.emit(CoreEvents.RELOAD_APPS, *name_wrapped)
    return dict(flash = 'Done!')

@app.route('css_themes')
def css_themes(ctx: Context):
    app_folder = os.path.dirname(__file__)
    pth = os.path
    css_dir = pth.join(app_folder, 'static/js/codemirror/theme')
    ret = []
    for nm in os.listdir(css_dir):
        if nm.endswith('.css') and pth.isfile(pth.join(css_dir, nm)):
            ret.append(nm[:-4])
    return dict(themes = ret)

@app.route('compile_py', method = 'POST')
def compile_py(ctx: Context):
    fp = ctx.request.json.get('fp')
    print('FP is ', fp)
    w23p_app = ctx.request.json.get('w23p_app')
    code = ctx.request.json.get('code')

    fp = fp[0] == '/' and fp[1:] or fp
    fp = os.path.join(APPS_FOLDER, w23p_app, fp)
    if not os.path.isfile(fp):
        raise HTTP(404, web2py_error =  '`%s` not found' % fp)
    if not fp.endswith('.py'):
        raise HTTP(404, web2py_error =  '`%s` not found a python file' % fp)

    code_raw = code if code is not None else fs2json.safe_read(fp)
    code = code_raw.rstrip().replace('\r\n', '\n') + '\n'
    highlight = None
    import _ast
    error = None
    try:
        compile(code, fp, "exec", _ast.PyCF_ONLY_AST)
    except Exception as e:
        # offset calculation is only used for textarea (start/stop)
        start = sum([len(line) + 1 for l, line
                     in enumerate(code_raw.split("\n"))
                     if l < e.lineno - 1])
        if e.text and e.offset:
            offset = e.offset - (len(e.text) - len(
                e.text.splitlines()[-1]))
        else:
            offset = 0
        highlight = {'start': start, 'end': start +
                     offset + 1, 'lineno': e.lineno, 'offset': offset}
        try:
            ex_name = e.__class__.__name__
        except:
            ex_name = 'unknown exception!'
        error = dict(line = e.lineno, col = offset, message = ex_name)
    return dict(err = error )

mounted_ctx: Context = app.mount()