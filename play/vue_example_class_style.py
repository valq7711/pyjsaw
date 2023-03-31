from pyjsaw.js_stuff.vuestuff import VDot as v, VTempl, template, slot
from pyjsaw.js_stuff import html as h
from pyjsaw.typing.jstyping import literal, String
from pyjsaw.typing.vuetyping import Vue
from pyjsaw.pyjs.vcollector import vc


# VTempl is special built-in
page_templ = VTempl({
    h.Div(): {
        h.Div({'aria-foo': 'bar'}, Class='some-class'): None,
        h.H3():
            '{{title}}',
        h.Div(Class='header'): {
            slot(name='header'):
                '[default header]'
        },
        h.Div(Class='content'): {
            slot(name='content'):
                'Sorry, it seems no content today'
        },
        h.Button(v.on(click='toggle_footer')):   # we can just 'footer_visible = !footer_visible'
            "{{footer_visible ? 'Hide' : 'Show' }} footer",

        h.Button(v.on({'click.stop': 'toggle_footer'})):
            "{{footer_visible ? 'Hide' : 'Show' }} footer",

        h.Div(
            v.show('footer_visible'),
            Class='footer'
        ): {
            slot(name='footer'): '[default footer]'
        },

        h.Form(): {
            h.Input(action='/qq'): None,
            h.Button(type='button'): 'qq',
        }
    }
})


@vc.component()
class Page:
    template = page_templ

    title = String, 'Page Title'

    def data(data_obj, vm: 'Page'):
        data_obj.footer_visible = False

    def toggle_footer(self):
        self.footer_visible = not self.footer_visible

    @vc.watch('footer_visible')
    def footer_visible_watcher(self, n, o):
        print(f'footer_visible changed from {o} to {n}')


app_templ = VTempl({
    Page(v.bind(title='app_title')): {
        template(v.slot(header=None)):
            'Page Header goes here',
        template(v.slot(content=None)):
            'Some content from App-component',
    }
})


@vc.component()
class App:

    template = app_templ

    def data(dobj):
        dobj.app_title = 'This title comes from App component'

    # register Page-component localy - just for example
    # to register globally: Vue.component('Page', Page)
    @literal
    class _extra:
        components = [Page]


app = Vue(App)   # just `App`,  not `App()` - no parens here as it is `@literal` not a real class

app.S_mount('#app')

'''
@vc.component()
class Some:
    # if type of template is string - it is treated as template, else - it is treated as prop
    template = page_templ

    # props are just class attrs
    title = {'type': String, 'default': 'Page Title'}

    # data is special method and there is a hack to provide autocomplete:
    # this method will be wrapped into a function which is included into a component definition as `data`-function,
    # data_obj is empty object (produced by wrapper) to fill in with data,
    # vm - is instance of component (i.e. `this` in normal vue-data function)
    # i.e. if you need a prop - you should vm.title (for example)
    def data(data_obj, vm: 'Page'):
        data_obj.footer_visible = False

    # just methods - become methods
    def toggle_footer(self):
        self.footer_visible = not self.footer_visible

    @vc.computed
    def some_computed(self):
        ...

    # 2-way computed
    @vc.computed
    @property
    def some_2way_computed(self):
        ...

    @vc.computed
    @some_2way_computed.setter
    def some_2way_computed(self):
        ...

    # `_extra` - special word
    # any extra prop to include in component definition as is
    @literal
    class _extra:
        name = __name__

    # `_postproc` - special word
    # the same as `_extra` but in functional style
    # vcd - vue component definition (aka vue options object)
    @staticmethod
    def _postproc(vcd):
        vcd.router = VueRouter()

'''
