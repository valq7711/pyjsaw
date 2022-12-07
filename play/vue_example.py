from pyjsaw.js_stuff.vuestuff import VDot as v, VTempl
from pyjsaw.js_stuff.js_obj import new
from pyjsaw.js_stuff import html as h
from vuetyping import Vue

templ = VTempl({
    h.Div(v.bind(Class="{'some-class': true}"), Class='some-class'): {
        h.Span(): '{{msg}}',
        h.Button(v.on(click='hidden_visible=!hidden_visible')): 'Toggle hidden',
        h.Div(v.If('hidden_visible'), v.For('idx in 5')): 'Now you see me! idx={{idx}}',
    }
})


def data():
    return {
        'msg': 'Hi there',
        'hidden_visible': False
    }


vc = Vue({
    'data': data,
    'template': templ
})

vc.S_mount('#app')

obj = {'a': 45, 'foo': 100}

for k in dir(obj):
    print(k)
