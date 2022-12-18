from typing import TypeVar, Type
from pyjsaw.js_stuff import __CompilerDirective__

__CompilerDirective__.TYPING_MODULE = True

arguments = object()
this = object()
undefined = object()


class JSON:
    @staticmethod
    def parse(jsn):
        ...


class RegExp:
    def exec(self, v):
        ...

    def test(self, v):
        ...


class window:
    ...


class Symbol:
    iterator = None


class Object:
    @staticmethod
    def getPrototypeOf(obj):
        ...

    def constructor(self):
        ...

    @staticmethod
    def defineProperty(obj: object, prop: str, descr: dict):
        ...

    def assign(self, *obj: object) -> object:
        ...

    @staticmethod
    def keys(obj: object) -> list:
        ...

    @staticmethod
    def hasOwnProperty(obj, p: str) -> bool:
        ...

    @staticmethod
    def getOwnPropertyDescriptors(obj) -> dict:
        ...

    @staticmethod
    def getOwnPropertyNames(obj) -> dict:
        ...


class String:
    ...


class Array:

    @staticmethod
    def isArray(obj: object) -> bool:
        ...

    def indexOf(self, obj) -> int:
        ...


class Set:

    def has(self, v: str) -> bool:
        ...


class Math:
    @staticmethod
    def max():
        ...

    @staticmethod
    def min():
        ...

    @staticmethod
    def pow():
        ...


def typeof(obj):
    ...


T = TypeVar('T')


class New:

    def __mul__(self, a: T) -> T:
        return a


new = New()


def literal(cls: Type[T]) -> T:
    return cls()


def promotestatic(cls: Type[T]) -> Type[T]:
    '''Expose class attrs at instance level via getters'''
    return cls


class Promise:

    @staticmethod
    def resolve(value):
        ...


class Error:
    ...


def setTimeout(fun, timeout):
    ...


def alert(msg):
    ...


iif = []


def iterkeys():
    '''Produce pure js for-in (fake function)'''
