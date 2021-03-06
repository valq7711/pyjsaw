
__all__ = [ 'XDict' ]

class XDict(dict):
    __slots__ = ()
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    __getitem__ = dict.get
    __getattr__ = dict.get
    __getnewargs__ = lambda self: getattr(dict,self).__getnewargs__(self)
    __repr__ = lambda self: f'<XDict {dict.__repr__(self)}>'
    __getstate__ = lambda self: None
    __copy__ = lambda self: XDict(self)

