(function(){
'use strict';
function ϟ_def_modules(){
    var modules;
    modules = {};
    function set_export(prop, get, set){
        var rs_mod, args, mod_id, def_prop;
        rs_mod = this;
        if(Array.isArray(prop)){
            for(args of prop){
                rs_mod.export(...args);
            };
            return;
        };
        if(typeof get === "string"){
            mod_id = get;
            get = () => modules[mod_id];
            set = null;
        };
        def_prop = {
            "configurable": true, 
            "enumerable": true, 
            "get": get
        };
        if(set){
            def_prop["set"] = set;
        };
        Object.defineProperty(rs_mod["exports"], prop, def_prop);
    };
    function def_module(mod_id){
        var rs_mod_id, rs_mod;
        rs_mod_id = `ϟ:${mod_id}`;
        rs_mod = modules[rs_mod_id] = {
            "ϟ_body": () => rs_mod["exports"], 
            "exports": {}, 
            "ϟ_invoked": false
        };
        rs_mod["export"] = set_export;
        function getter(){
            var mod;
            mod = modules[rs_mod_id];
            if(mod["ϟ_invoked"]){
                return mod["exports"];
            };
            mod["ϟ_invoked"] = true;
            return mod["ϟ_body"]()["exports"];
        };
        function setter(v){
            modules[rs_mod_id]["exports"] = v;
        };
        Object.defineProperty(modules, mod_id, {
            "enumerable": true, 
            "get": getter, 
            "set": setter
        });
        return rs_mod;
    };
    Object.defineProperty(modules, "ϟ_defmod", {
        "configurable": false, 
        "enumerable": false, 
        "value": def_module
    });
    return modules;
}
var ϟ_modules = ϟ_def_modules();
var ϟ_defmod = ϟ_modules.ϟ_defmod;
ϟ_defmod("baselib");
ϟ_modules["ϟ:baselib"].ϟ_body = function (){
    var STR_CTR, ARR_CTR, SET_CTR;
    var __name__ = "baselib";
    STR_CTR = "".constructor;
    ARR_CTR = [].constructor;
    SET_CTR = Set.prototype.constructor;
    function is_in(v, obj){
        if(typeof obj.indexOf === "function"){
            return obj.indexOf(v) !== -1;
        }else if(typeof obj.has === "function"){
            return obj.has(v);
        };
        return obj.hasOwnProperty(v);
    };
    function iterable(obj){
        var octr;
        octr = obj.constructor;
        if(octr === STR_CTR || Symbol.iterator in obj){
            return obj;
        };
        return Object.keys(obj);
    };
    function len(obj){
        var octr;
        octr = obj.constructor;
        if(octr === STR_CTR || octr === ARR_CTR){
            return obj.length;
        };
        if(octr === SET_CTR){
            return obj.size;
        };
        return Object.keys(obj).length;
    };
    function type(obj){
        if(obj === null){
            return null;
        };
        return Object.getPrototypeOf(obj).constructor;
    };
    function max(a){
        return Math.max.apply(null, Array.isArray(a) ? a : arguments);
    };
    function min(a){
        return Math.max.apply(null, Array.isArray(a) ? a : arguments);
    };
    function reversed(arr){
        var tmp;
        tmp = arr.slice(0);
        return tmp.reverse();
    };
    function sorted(arr){
        var tmp;
        tmp = arr.slice(0);
        return tmp.sort();
    };
    function hasattr(obj, name){
        return name in obj;
    };
    function *dir(obj){
        var seen, k, v, cur;
        seen = new Set();
        for([k, v] of Object.entries(Object.getOwnPropertyDescriptors(obj))){
            seen.add(k);
            yield [k, v];
        };
        cur = Object.getPrototypeOf(obj);
        while(cur){
            if(cur.constructor && cur.constructor === Object){
                break;
            };
            for([k, v] of Object.entries(Object.getOwnPropertyDescriptors(cur))){
                if(!seen.has(k)){
                    seen.add(k);
                    yield [k, v];
                };
            };
            cur = Object.getPrototypeOf(cur);
        };
    };
    function decor(){
        var args, fun, d;
        args = [...arguments];
        fun = args.pop();
        args.reverse();
        for(d of args){
            fun = d(fun);
        };
        return fun;
    };
    
    // exports
    var ϟ_mod = ϟ_modules["ϟ:baselib"];
    Object.assign(ϟ_modules["ϟ:baselib"].exports, {__name__, STR_CTR, ARR_CTR, SET_CTR, is_in, iterable, len, type, max, min, reversed, sorted, hasattr, dir, decor});
    return ϟ_mod;
};

ϟ_defmod("pyjsaw.pyjs");
ϟ_defmod("pyjsaw.pyjs.vcollector");
ϟ_modules["ϟ:pyjsaw.pyjs"].export("vcollector", "pyjsaw.pyjs.vcollector");
ϟ_modules["ϟ:pyjsaw.pyjs"].ϟ_body = function (){
    var __name__ = "pyjsaw.pyjs";
    
    // exports
    var ϟ_mod = ϟ_modules["ϟ:pyjsaw.pyjs"];
    ϟ_mod.export([
        ["__name__", ()=>__name__, null]
    ]);
    return ϟ_mod;
};

 ϟ_modules["ϟ:pyjsaw.pyjs.vcollector"].ϟ_body = function (){
    var _SPECIAL_VUEMETHODS, vc, __all__;
    var __name__ = "pyjsaw.pyjs.vcollector";
    _SPECIAL_VUEMETHODS = new Set(["beforeCreate", "created", "beforeMount", "mounted", "beforeUpdate", "updated", "activated", "deactivated", "beforeDestroy", "destroyed", "render"]);
    function is_hook(name){
        return _SPECIAL_VUEMETHODS.has(name);
    };
    function is_special(name){
        return (new RegExp("^((_.+)|constructor)$")).test(name);
    };
    function vopt_from_class(cls){
        var v_collector, vcd, bases, data_setup, meth_name, v, prop_name, prop, prop_, keys, ϟ_1, i, ret, c;
        v_collector = cls.__vue_opt__;
        vcd = {};
        vcd.name = cls.name;
        vcd.props = {};
        vcd.methods = {};
        if(v_collector){
            bases = v_collector.bases;
            if(bases && bases.length){
                vcd.mixins = v_collector.bases;
            };
            vcd.computed = v_collector._computed;
            vcd.directives = v_collector._directives;
            vcd.filters = v_collector._filters;
            vcd.watch = v_collector._watch;
        };
        data_setup = cls.prototype.data;
        if(data_setup){
            function data(){
                var data_obj;
                data_obj = {};
                data_setup.call(data_obj, [this]);
                return data_obj;
            };
            vcd.data = data;
        };
        for([meth_name, v] of Object.entries(Object.getOwnPropertyDescriptors(cls.prototype))){
            if(meth_name === "data" || is_special(meth_name) || v_collector && v_collector.__collected__[meth_name] || !v.value){
                continue;
            };
            if(is_hook(meth_name)){
                vcd[meth_name] = v.value;
            }else{
                vcd.methods[meth_name] = v.value;
            };
        };
        for(prop_name in cls){
            if(prop_name === "_extra" || prop_name.startsWith("__")){
                continue;
            };
            if(prop_name === "template" && typeof cls[prop_name] === "string"){
                vcd[prop_name] = cls[prop_name];
            }else{
                prop = cls[prop_name];
                if(Array.isArray(prop)){
                    prop_ = {};
                    keys = ["type", "default", "required", "validator"];
                    ϟ_1 = 0;
                    for(v of prop){
                        i = ϟ_1++;
                        if(v === undefined){
                            continue;
                        };
                        prop_[keys[i]] = v;
                    };
                    prop = prop_;
                };
                vcd.props[prop_name] = prop;
            };
        };
        if("_extra" in cls){
            Object.assign(vcd, cls["_extra"]);
        };
        if("_postproc" in cls){
            ret = cls["_postproc"](vcd);
            if(ret){
                vcd = ret;
            };
        };
        if(Array.isArray(vcd.components)){
            vcd.components = (() => {var ϟ_2 = {}; for(c of vcd.components){ϟ_2[c.name] = c;}; return ϟ_2})();
        };
        return vcd;
    };
    class VCollector{
        get __class__(){
            return this.constructor;
        };
        constructor(){
            var self;
            self = this;
            self._methods = null;
            self._computed = null;
            self._watch = null;
            self._filters = null;
            self._directives = null;
            self.__current__ = null;
            self.__collected__ = {};
        };
        _collector(opt_name, extra){
            var self;
            self = this;
            self.__current__ = {
                "__collected__": {}
            };
            if(extra){
                Object.assign(self.__current__, extra);
            };
            function wrapper(cls){
                cls[opt_name] = self.__current__;
                self.__current__ = null;
                return vopt_from_class(cls);
            };
            return wrapper;
        };
        component(){
            var self, bases;
            self = this;
            bases = [...arguments];
            return self._collector("__vue_opt__", {
                "bases": bases
            });
        };
        _reg_as(reg_as, name, fun_opt){
            var self, cur, computed, fun;
            self = this;
            cur = self.__current__;
            if(!cur[reg_as]){
                cur[reg_as] = {};
            }else if(reg_as === "_computed"){
                computed = cur[reg_as];
                if(computed[name]){
                    computed[name] = {
                        "get": computed[name], 
                        "set": fun_opt
                    };
                    return fun_opt;
                };
            };
            cur[reg_as][name] = fun_opt;
            fun = (fun_opt.handler) ? fun_opt.handler : fun_opt;
            cur.__collected__[fun.name] = true;
            return fun;
        };
        computed(fun){
            var self, fun_name;
            self = this;
            fun_name = fun.__name__ || fun.name;
            if(fun_name.startsWith("get ") || fun_name.startsWith("set ")){
                fun_name = fun_name.slice(4);
            };
            return self._reg_as("_computed", fun_name, fun);
        };
        filter(fun){
            var self, fun_name;
            self = this;
            fun_name = fun.__name__ || fun.name;
            return self._reg_as("_filters", fun_name, fun);
        };
        directive(fun){
            var self, fun_name;
            self = this;
            fun_name = fun.__name__ || fun.name;
            return self._reg_as("_directives", fun_name, fun);
        };
        watch(name, opt){
            var self;
            self = this;
            if(!opt){
                opt = {};
            };
            function wrapper(fun){
                opt.handler = fun;
                return self._reg_as("_watch", name, opt);
            };
            return wrapper;
        };
    };

    vc = new VCollector();
    __all__ = [VCollector, vc];
    
    // exports
    var ϟ_mod = ϟ_modules["ϟ:pyjsaw.pyjs.vcollector"];
    ϟ_mod.export([
        ["__name__", ()=>__name__, null],
        ["VCollector", ()=>VCollector, (v)=>{if (typeof VCollector !== "undefined") VCollector = v;}],
        ["vc", ()=>vc, (v)=>{if (typeof vc !== "undefined") vc = v;}]
    ]);
    return ϟ_mod;
};
(function (){
    var page_templ, ϟ_1, ϟ_2, ϟ_3, app_templ, ϟ_4, ϟ_5, app;
    var __name__ = "__main__";
    var vc = ϟ_modules["pyjsaw.pyjs.vcollector"].vc;
    page_templ = '<div><div some="45" aria-foo="bar"></div><h3>{{title}}</h3><div class="header"><slot name="header">[default header]</slot></div><div class="content"><slot name="content">Sorry, it seems no content today</slot></div><button v-on:click="toggle_footer">{{footer_visible ? \'Hide\' : \'Show\' }} footer</button><button v-on:click.stop="toggle_footer">{{footer_visible ? \'Hide\' : \'Show\' }} footer</button><div v-show="footer_visible" class="footer"><slot name="footer">[default footer]</slot></div><form><input action="/qq"/><button type="button">qq</button></form></div>';
    ϟ_1 = vc.component();
    class Page{
        get __class__(){
            return this.constructor;
        };
        static template = page_templ;
        static title = [String, "Page Title"];
        data(vm){
            var data_obj;
            data_obj = this;
            data_obj.footer_visible = false;
        };
        toggle_footer(){
            var self;
            self = this;
            self.footer_visible = !self.footer_visible;
        };
        footer_visible_watcher(n, o){
            var self;
            self = this;
            console.log(`footer_visible changed from ${o} to ${n}`);
        };
    };
    Page.prototype.footer_visible_watcher = (ϟ_2=vc.watch("footer_visible")(Page.prototype.footer_visible_watcher), ϟ_2);
    Page = (ϟ_3=ϟ_1(Page), ϟ_3);

    app_templ = '<Page v-bind:title="app_title"><template v-slot:header>Page Header goes here</template><template v-slot:content>Some content from App-component</template></Page>';
    ϟ_4 = vc.component();
    class App{
        get __class__(){
            return this.constructor;
        };
        static template = app_templ;
        data(){
            var dobj;
            dobj = this;
            dobj.app_title = "This title comes from App component";
        };
        static _extra = {
            components: [Page]
        };
    };
    App = (ϟ_5=ϟ_4(App), ϟ_5);

    app = new Vue(App);
    app.$mount("#app");
    "\n@vc.component()\nclass Some:\n    # if type of template is string - it is treated as template, else - it is treated as prop\n    template = page_templ\n\n    # props are just class attrs\n    title = {'type': String, 'default': 'Page Title'}\n\n    # data is special method and there is a hack to provide autocomplete:\n    # this method will be wrapped into a function which is included into a component definition as `data`-function,\n    # data_obj is empty object (produced by wrapper) to fill in with data,\n    # vm - is instance of component (i.e. `this` in normal vue-data function)\n    # i.e. if you need a prop - you should vm.title (for example)\n    def data(data_obj, vm: 'Page'):\n        data_obj.footer_visible = False\n\n    # just methods - become methods\n    def toggle_footer(self):\n        self.footer_visible = not self.footer_visible\n\n    @vc.computed\n    def some_computed(self):\n        ...\n\n    # 2-way computed\n    @vc.computed\n    @property\n    def some_2way_computed(self):\n        ...\n\n    @vc.computed\n    @some_2way_computed.setter\n    def some_2way_computed(self):\n        ...\n\n    # `_extra` - special word\n    # any extra prop to include in component definition as is\n    @literal\n    class _extra:\n        name = __name__\n\n    # `_postproc` - special word\n    # the same as `_extra` but in functional style\n    # vcd - vue component definition (aka vue options object)\n    @staticmethod\n    def _postproc(vcd):\n        vcd.router = VueRouter()\n\n";
})()
})()