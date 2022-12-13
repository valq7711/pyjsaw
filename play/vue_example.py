from pyjsaw.js_stuff.vuestuff import VDot as v, VTempl
from pyjsaw.js_stuff import html as h
from pyjsaw.typing.jstyping import literal
from pyjsaw.typing.vuetyping import Vue

templ = VTempl({
    h.Div(v.bind(Class="{'some-class': true}"), Class='some-static-class'): {
        h.Span(): '{{msg}}',
        h.Button(v.on(click='hidden_visible=!hidden_visible')): 'Toggle hidden',
        h.Div(v.If('hidden_visible'), v.For('idx in 5')): 'Now you see me! idx={{idx}}',
        h.Button(v.on(click='some')): 'Run method (see console)',
    }
})


@Vue
@literal
class vc:
    template = templ

    def data(self):
        return {
            'msg': 'Hi there',
            'hidden_visible': False
        }

    @literal
    class methods('vc'):
        def some(self):
            print('some-method invoked')


vc.S_mount('#app')
