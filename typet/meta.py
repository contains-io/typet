# -*- coding: utf-8 -*-
"""A module containing common metaclasses.

Classes:
    metaclass: A class decorator that will create the class using multiple
        metaclasses.
    Singleton: A metaclass to force a class to only ever be instantiated once.
    Uninstantiable: A metaclass that causes a class to be uninstantiable.
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
    'Uninstantiable',
)


def metaclass(*metaclasses):
    # type: (*type) -> Callable[[type], type]
    """Create the class using all metaclasses.

    The primary metaclass will be the metaclass already defined on the class.

    Args:
        metaclasses: A tuple of metaclasses that will be used to generate and
            replace a specified class.

    Returns:
        A decorator that will recreate the class using the specified
        metaclasses.
    """
    def _inner(cls):
        metabases = collections.OrderedDict(
            (c, None) for c in (metaclasses + (type(cls),))
        ).keys()
        class _Meta(*metabases):
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


class Uninstantiable(type):
    """A metaclass that disallows instantiation."""

    def __call__(cls, *args, **kwargs):
        # type: (*Any, **Any) -> None
        """Do not allow the class to be instantiated."""
        raise TypeError('Type {} cannot be instantiated.'.format(cls.__name__))
