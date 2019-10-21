# -*- coding: utf-8 -*-
"""A module containing basic types.

Classes:
    DefType: A union of function and method types.
    NoneType: An alias for type(None)
"""

from __future__ import absolute_import
from __future__ import unicode_literals

import types
import typing


__all__ = ("DefType", "NoneType")


DefType = typing.Union[types.FunctionType, types.MethodType]
NoneType = type(None)  # pylint: disable=redefined-builtin
