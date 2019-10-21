# -*- coding: utf-8 -*-
"""Tests for py3.6+ annotation type hint casting."""

from __future__ import unicode_literals

import pytest

import typing
import typet


def test_strict_object():
    """Simple test to verify basic StrictObject functionality."""

    class X(typet.StrictObject):
        x: str

    x = X("initial")
    x.x = "hello"
    assert isinstance(x.x, str)
    assert x.x == "hello"
    with pytest.raises(TypeError):
        x.x = 5


def test_object():
    """Simple test to verify basic Object functionality."""

    class X(typet.Object):
        x: str = None

    x = X()
    x.x = 5
    assert isinstance(x.x, str)
    assert x.x == "5"


def test_object_failure():
    """Simple test to verify basic Object failure functionality."""

    class X(typet.Object):
        x: int = None

    x = X()
    x.x = None
    with pytest.raises(TypeError):
        x.x = "not an integer"


def test_optional_unassigned():
    """Verify that an unassigned Optional attribute is optional in __init__."""

    class X(typet.Object):
        x: typing.Optional[int]

    X()
