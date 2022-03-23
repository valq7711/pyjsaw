from enum import Enum, auto

arguments = object()

this = object()
undefined = object()

class __RSDirectives__:
    EXPORTS_AS_DICT = None

    def EMBED(name):
        pass

class Symbol(Enum):
    iterator = auto()


class Object:
    def defineProperty(obj: object, prop: str, descr: dict):
        ...

    def assign(*obj: object) -> object:
        ...

    def keys(obj: object) -> list:
        ...

class Array:
    def isArray(obj: object) -> bool:
        ...

class String:
    ...

class Set:
    ...

class Math:
    def max():
        ...

    def min():
        ...

    def pow():
        ...

def typeof(obj):
    ...


