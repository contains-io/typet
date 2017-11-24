# -*- coding: utf-8 -*-
"""A module containing common metaclasses.

Classes:
    Singleton: A metaclass to force a class to only ever be instantiated once.
    Uninstantiable: A metaclass that causes a class to be uninstantiable.
"""

from __future__ import unicode_literals

from typingplus import Any  # noqa: F401 pylint: disable=unused-import


__all__ = (
    'Singleton',
    'Uninstantiable',
)


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
