# -*- coding: utf-8 -*-
"""A module containing common metaclasses and utilites for working with them.

Metaclasses:
    Singleton: A metaclass to force a class to only ever be instantiated once.
    Uninstantiable: A metaclass that causes a class to be uninstantiable.

Decorators:
    metaclass: A class decorator that will create the class using multiple
        metaclasses.
    singleton: A class decorator that will make the class a singleton, even if
        the class already has a metaclass.
"""

from __future__ import unicode_literals

import collections

from typingplus import (  # noqa: F401 pylint: disable=unused-import
    Any,
    Callable
)
import six


__all__ = (
    'metaclass',
    'Singleton',
    'singleton',
    'Uninstantiable',
)


def metaclass(*metaclasses):
    # type: (*type) -> Callable[[type], type]
    """Create the class using all metaclasses.

    Args:
        metaclasses: A tuple of metaclasses that will be used to generate and
            replace a specified class.

    Returns:
        A decorator that will recreate the class using the specified
        metaclasses.
    """
    def _inner(cls):
        # pragma pylint: disable=unused-variable
        metabases = tuple(collections.OrderedDict(  # noqa: F841
            (c, None) for c in (metaclasses + (type(cls),))
        ).keys())
        # pragma pylint: enable=unused-variable
        _Meta = metabases[0]
        for base in metabases[1:]:
            class _Meta(base, _Meta):  # pylint: disable=function-redefined
                pass
        return six.add_metaclass(_Meta)(cls)
    return _inner


class Singleton(type):
    """A metaclass to turn a class into a singleton."""

    __instance__ = None  # type: type

    def __call__(cls, *args, **kwargs):
        # type: (*Any, **Any) -> type
        """Instantiate the class only once."""
        if not cls.__instance__:
            cls.__instance__ = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.__instance__


singleton = metaclass(Singleton)


class Uninstantiable(type):
    """A metaclass that disallows instantiation."""

    def __call__(cls, *args, **kwargs):
        # type: (*Any, **Any) -> None
        """Do not allow the class to be instantiated."""
        raise TypeError('Type {} cannot be instantiated.'.format(cls.__name__))
