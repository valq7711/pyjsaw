from pyjsaw.js_stuff.vuestuff import VDot as v, VTempl, template, slot
from pyjsaw.js_stuff import html as h
from pyjsaw.typing.jstyping import literal, String
from pyjsaw.typing.vuetyping import Vue


# VTempl is special built-in
page_templ = VTempl({
    h.Div(): {
        h.H3():
            '{{title}}',
        h.Div(Class='header'): {
            slot(name='header'): '[default header]'
        },
        h.Div(Class='content'): {
            slot(name='content'): 'Sorry, it seems no content today'
        },
        h.Button(v.on(click='toggle_footer')):   # we can just 'footer_visible = !footer_visible'
            "{{footer_visible ? 'Hide' : 'Show' }} footer",
        h.Div(v.show('footer_visible'), Class='footer'): {
            slot(name='footer'): '[default footer]'
        },
    }
})


@literal
class Page:
    template = page_templ
    # do not use `dict(...)` as we in js,
    # but you can try Object(foo='bar')
    props = {
        'title': {'type': String, 'default': 'Page Title'}
    }

    def data(self):
        return {
            'footer_visible': False
        }

    @literal
    class methods:
        def toggle_footer(self):
            self.footer_visible = not self.footer_visible


app_templ = VTempl({
    Page(v.bind(title='app_title')): {
        template(v.slot(header=None)):
            'Page Header goes here',
        template(v.slot(content=None)):
            'Some content from App-component',
    }
})


@literal
class App:
    template = app_templ

    def data(self):
        return {
            'app_title': 'This title comes from App component'
        }

    # register Page-component localy - just for example
    # to register globally: Vue.component('Page', Page)
    components = {
        'Page': Page
    }


app = Vue(App)   # just `App`,  not `App()` - no parens here as it is `@literal` not a real class

app.S_mount('#app')
