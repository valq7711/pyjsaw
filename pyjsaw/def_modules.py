from pyjsaw.js_stuff.js_obj import Object, Array, this, typeof


def __def_modules__():
    modules = {}

    def set_export(prop, get, set):
        rs_mod = this
        if Array.isArray(prop):
            f"{'for(args of prop){rs_mod.export(...args)}'}"
            return

        if typeof(get) == 'string':
            mod_id = get
            get = lambda: modules[mod_id]
            set = None

        def_prop = {
            'configurable': True,
            'enumerable': True,
            'get': get,
        }

        if set:
            def_prop['set'] = set

        Object.defineProperty(rs_mod["exports"], prop, def_prop)

    def def_module(mod_id):
        rs_mod_id = f"{{PREFIX}}:{mod_id}"
        rs_mod = modules[rs_mod_id] = {
            "{PREFIX}_body": lambda: rs_mod["exports"],
            "exports": {},
            "{PREFIX}_invoked": False,
        }
        rs_mod["export"] = set_export

        def getter():
            # module getter
            mod = modules[rs_mod_id]
            if mod["{PREFIX}_invoked"]:
                return mod["exports"]
            mod["{PREFIX}_invoked"] = True
            return mod["{PREFIX}_body"]()["exports"]

        def setter(v):
            modules[rs_mod_id]["exports"] = v

        Object.defineProperty(modules, mod_id, {
            'enumerable': True,
            'get': getter,
            'set': setter
        })
        return rs_mod

    Object.defineProperty(modules, '{PREFIX}_defmod', {
        'configurable': False,
        'enumerable': False,
        'value': def_module
    })
    return modules
