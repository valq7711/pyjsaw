from pyjsaw.typing.jstyping import Set, RegExp, Object, iif, this, iterkeys, typeof, Array, undefined

_SPECIAL_VUEMETHODS = Set([
    'beforeCreate', 'created',
    'beforeMount', 'mounted',
    'beforeUpdate', 'updated',
    'activated', 'deactivated',
    'beforeDestroy', 'destroyed',
    'render',
])


def is_hook(name):
    return _SPECIAL_VUEMETHODS.has(name)


def is_special(name):
    return RegExp('^((_.+)|constructor)$').test(name)


def vopt_from_class(cls):
    v_collector = cls.__vue_opt__
    vcd = {}  # vue component definition
    vcd.name = cls.name
    vcd.props = {}
    vcd.methods = {}
    if v_collector:
        bases = v_collector.bases
        if bases and bases.length:
            vcd.mixins = v_collector.bases
        vcd.computed = v_collector._computed
        vcd.directives = v_collector._directives
        vcd.filters = v_collector._filters
        vcd.watch = v_collector._watch

    # process data
    data_setup = cls.prototype.data
    if data_setup:
        def data():
            data_obj = {}
            data_setup.call(data_obj, this)
            return data_obj
        vcd.data = data

    # collect methods
    for meth_name, v in Object.entries(Object.getOwnPropertyDescriptors(cls.prototype)):
        if (
            meth_name == 'data' or is_special(meth_name) or v_collector and v_collector.__collected__[meth_name]
            or not v.value
        ):
            continue
        if is_hook(meth_name):
            vcd[meth_name] = v.value
        else:
            vcd.methods[meth_name] = v.value

    # collect props
    for prop_name in iterkeys(cls):
        if prop_name == '_extra' or prop_name.startsWith('__'):
            continue
        # treat `template` as template if it is only string
        if prop_name == 'template' and typeof(cls[prop_name]) == 'string':
            vcd[prop_name] = cls[prop_name]
        else:
            prop = cls[prop_name]
            if Array.isArray(prop):
                prop_ = {}
                keys = ['type', 'default', 'required', 'validator']
                for i, v in enumerate(iter(prop)):
                    if v is undefined:
                        continue
                    prop_[keys[i]] = v
                prop = prop_
            vcd.props[prop_name] = prop

    # set extra options and call postproc
    if hasattr(cls, '_extra'):
        Object.assign(vcd, cls['_extra'])

    if hasattr(cls, '_postproc'):
        ret = cls['_postproc'](vcd)
        if ret:
            vcd = ret

    if Array.isArray(vcd.components):
        # assuming it is array of components and each component has `name`-attr
        vcd.components = {c.name: c for c in iter(vcd.components)}

    return vcd


class VCollector:
    def __init__(self):
        self._methods = None
        self._computed = None
        self._watch = None
        self._filters = None
        self._directives = None

        self.__current__ = None
        self.__collected__ = {}

    def _collector(self, opt_name, extra):
        self.__current__ = {
            '__collected__': {}
        }
        if extra:
            Object.assign(self.__current__, extra)

        def wrapper(cls):
            cls[opt_name] = self.__current__
            self.__current__ = None
            return vopt_from_class(cls)
        return wrapper

    def component(self, *bases):
        return self._collector('__vue_opt__', {'bases': bases})

    def _reg_as(self, reg_as, name, fun_opt):
        cur = self.__current__
        if not cur[reg_as]:
            cur[reg_as] = {}
        elif reg_as == '_computed':
            # maybe 2-way
            computed = cur[reg_as]
            if computed[name]:
                computed[name] = {
                    'get': computed[name],
                    'set': fun_opt
                }
                return fun_opt

        cur[reg_as][name] = fun_opt
        fun = iif[fun_opt.handler: fun_opt.handler, fun_opt]
        cur.__collected__[fun.name] = True
        return fun

    def computed(self, fun):
        fun_name = fun.__name__ or fun.name
        if fun_name.startsWith('get ') or fun_name.startsWith('set '):
            fun_name = fun_name[4:]
        return self._reg_as('_computed', fun_name, fun)

    def filter(self, fun):
        fun_name = fun.__name__ or fun.name
        return self._reg_as('_filters', fun_name, fun)

    def directive(self, fun):
        fun_name = fun.__name__ or fun.name
        return self._reg_as('_directives', fun_name, fun)

    def watch(self, name, opt):
        if not opt:
            opt = {}

        def wrapper(fun):
            opt.handler = fun
            return self._reg_as('_watch', name, opt)
        return wrapper


vc = VCollector()

__all__ = [VCollector, vc]
