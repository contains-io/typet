# -*- coding: utf-8 -*-
"""A module containing common metaclasses and utilites for working with them.

Metaclasses:
    Singleton: A metaclass to force a class to only ever be instantiated once.
    IdempotentSingleton: A metaclass that will force a class to only create one
        instance, but will call __init__ on the instance when new instantiation
        attempts occur.
    Uninstantiable: A metaclass that causes a class to be uninstantiable.

Decorators:
    metaclass: A class decorator that will create the class using multiple
        metaclasses.
    singleton: A class decorator that will make the class a singleton, even if
        the class already has a metaclass.
"""

from __future__ import unicode_literals


from typing import (  # noqa: F401 pylint: disable=unused-import
    Any,
    Callable,
)
import collections

import six


__all__ = (
    "metaclass",
    "Singleton",
    "singleton",
    "IdempotentSingleton",
    "Uninstantiable",
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
        metabases = tuple(
            collections.OrderedDict(  # noqa: F841
                (c, None) for c in (metaclasses + (type(cls),))
            ).keys()
        )
        # pragma pylint: enable=unused-variable
        _Meta = metabases[0]
        for base in metabases[1:]:

            class _Meta(base, _Meta):  # pylint: disable=function-redefined
                pass

        return six.add_metaclass(_Meta)(cls)

    return _inner


class Singleton(type):
    """A metaclass to turn a class into a singleton.

    If the instance already exists, Singleton will attempt to call
    __singleton__ on the instance to allow the instance to update if necessary.
    """

    __instance__ = None  # type: type

    def __call__(cls, *args, **kwargs):
        # type: (*Any, **Any) -> type
        """Instantiate the class only once."""
        if not cls.__instance__:
            cls.__instance__ = super(Singleton, cls).__call__(*args, **kwargs)
        else:
            try:
                cls.__instance__.__singleton__(*args, **kwargs)  # type: ignore
            except (AttributeError, TypeError):
                pass
        return cls.__instance__


class IdempotentSingleton(Singleton):
    """A metaclass to turn a class into a singleton.

    If the instance already exists, IdempotentSingleton will call __init__ on
    the existing instance with the arguments given.
    """

    def __call__(cls, *args, **kwargs):
        # type: (*Any, **Any) -> type
        """Create one instance of the class and reinstantiate as necessary."""
        if not cls.__instance__:
            cls.__instance__ = super(IdempotentSingleton, cls).__call__(
                *args, **kwargs
            )
        else:
            try:
                cls.__instance__.__init__(*args, **kwargs)  # type: ignore
            except (AttributeError, TypeError):
                pass
        return cls.__instance__


singleton = metaclass(Singleton)


class Uninstantiable(type):
    """A metaclass that disallows instantiation."""

    def __call__(cls, *args, **kwargs):
        # type: (*Any, **Any) -> None
        """Do not allow the class to be instantiated."""
        raise TypeError("Type {} cannot be instantiated.".format(cls.__name__))
