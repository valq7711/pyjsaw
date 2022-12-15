(function(){
function ϟ_def_modules(){
    var modules;
    modules = {};
    function set_export(prop, get, set){
        var rs_mod, mod_id, def_prop;
        rs_mod = this;
        if(Array.isArray(prop)){
            for(args of prop){rs_mod.export(...args)};
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
        tmp = arr.slice(None, None);
        return tmp.reverse();
    };
    function sorted(arr){
        var tmp;
        tmp = arr.slice(None, None);
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

(function (){
    var page_templ, Page, app_templ, App, app;
    var __name__ = "__main__";
    page_templ = '<div><h3>{{title}}</h3><div class="header"><slot name="header">[default header]</slot></div><div class="content"><slot name="content">Sorry, it seems no content today</slot></div><button v-on:click="toggle_footer">{{footer_visible ? \'Hide\' : \'Show\' }} footer</button><div v-show="footer_visible" class="footer"><slot name="footer">[default footer]</slot></div></div>';
    Page = {
        template: page_templ, 
        props: {
            title: {
                "type": String, 
                "default": "Page Title"
            }
        }, 
        data: function (){
            var self;
            self = this;
            return {
                "footer_visible": false
            };
        }, 
        methods: {
            toggle_footer: function (){
                var self;
                self = this;
                self.footer_visible = !self.footer_visible;
            }
        }
    };
    app_templ = '<Page v-bind:title="app_title"><template v-slot:header>Page Header goes here</template><template v-slot:content>Some content from App-component</template></Page>';
    App = {
        template: app_templ, 
        data: function (){
            var self;
            self = this;
            return {
                "app_title": "This title comes from App component"
            };
        }, 
        components: {
            "Page": Page
        }
    };
    app = new Vue(App);
    app.$mount("#app");
})()
})()