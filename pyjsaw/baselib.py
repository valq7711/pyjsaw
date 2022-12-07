from typing import Union
from pyjsaw.js_stuff.js_obj import typeof, Symbol, Object, Set, String, Math, Array, arguments, __CompilerDirective__

STR_CTR = ''.constructor
ARR_CTR = [].constructor
SET_CTR = Set.prototype.constructor


def is_in(v, obj: Union[Array, Object, Set]):
    if typeof(obj.indexOf) == 'function':
        return obj.indexOf(v) != -1
    elif typeof(obj.has) == 'function':
        return obj.has(v)
    return obj.hasOwnProperty(v)


def iterable(obj: Object):
    octr = obj.constructor
    if octr is STR_CTR or hasattr(obj, Symbol.iterator):
        return obj
    return Object.keys(obj)


def len(obj):
    octr = obj.constructor
    if octr is STR_CTR or octr is ARR_CTR:
        return obj.length
    if octr is SET_CTR:
        return obj.size
    return Object.keys(obj).length


def isstr(s):
    return s.constructor is STR_CTR or isinstance(s, String)


def max(a):
    return Math.max.apply(None, a if Array.isArray(a) else arguments)


def min(a):
    return Math.max.apply(None, a if Array.isArray(a) else arguments)


def reversed(arr):
    tmp = arr[:]
    return tmp.reverse()


def sorted(arr):
    tmp = arr[:]
    return tmp.sort()


def hasattr(obj, name):
    # don't worry:
    # hasattr-call `hasattr(obj, a)` always compiled into `a in obj`
    return hasattr(obj, name)


def dir(obj):
    for p in dir(obj):
        yield p


def decor(*args):
    fun = args.pop()
    args.reverse()
    for d in iter(args):
        fun = d(fun)
    return fun


__CompilerDirective__.EXPORTS_AS_DICT = True
