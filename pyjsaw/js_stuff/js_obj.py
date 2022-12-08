from typing import TypeVar, Generic, Type
from enum import Enum, auto

arguments = object()

this = object()
undefined = object()


class Symbol(Enum):
    iterator = auto()


class Object:
    def constructor():
        ...

    def defineProperty(obj: object, prop: str, descr: dict):
        ...

    def assign(*obj: object) -> object:
        ...

    def keys(obj: object) -> list:
        ...

    def hasOwnProperty(obj, p: str) -> bool:
        ...


class Array:

    @staticmethod
    def isArray(obj: object) -> bool:
        ...

    def indexOf(self, obj) -> int:
        ...

class String:
    ...

class Set:

    def has(self, v: str) -> bool:
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


T = TypeVar('T')


class New:

    def __mul__(self, a: T) -> T:
        return a


new = New()


def literal(cls: Type[T]) -> T:
    return cls()
