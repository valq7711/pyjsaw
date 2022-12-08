from pyjsaw.js_stuff.vuestuff import VDot as v, VTempl
from pyjsaw.js_stuff.js_obj import new, literal
from pyjsaw.js_stuff import html as h
from vuetyping import Vue

templ = VTempl({
    h.Div(v.bind(Class="{'some-class': true}"), Class='some-class'): {
        h.Span(): '{{msg}}',
        h.Button(v.on(click='hidden_visible=!hidden_visible')): 'Toggle hidden',
        h.Div(v.If('hidden_visible'), v.For('idx in 5')): 'Now you see me! idx={{idx}}',
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


vc.S_mount('#app')
