# -*- coding: utf-8 -*-
"""Tests for annotation type hint casting."""

from typing import (  # noqa: F401 pylint: disable=unused-import
    Any,
    Optional,
)
import os.path
import uuid

import pytest
import six

from typet.typing import is_instance
import typet


def test_bounded_type():
    """Test the bounded type object."""
    with pytest.raises(TypeError):
        BoundedInt = typet.Bounded[int]
    with pytest.raises(TypeError):
        BoundedInt = typet.Bounded[int, 10:20, lambda x: x, None]
    BoundedInt = typet.Bounded[int, 10:20]
    with pytest.raises(ValueError):
        BoundedInt(5)
    assert BoundedInt(10) == 10
    assert BoundedInt(15) == 15
    assert BoundedInt(20) == 20
    with pytest.raises(ValueError):
        BoundedInt(25)
    BoundedStr = typet.Bounded[str, 1:5, len]
    with pytest.raises(ValueError):
        BoundedStr("")
    assert BoundedStr("abc") == "abc"
    with pytest.raises(ValueError):
        BoundedStr("abcdef")
    assert str(BoundedInt) == "typet.validation.Bounded[int, 10:20]"
    assert typet.Bounded[Any, 10:20](15) == 15
    assert typet.Bounded["int", 20](15) == 15
    assert typet.Bounded["int", 10:](15) == 15


def test_length_type():
    """Test the bounded length type object."""
    with pytest.raises(TypeError):
        LengthBoundedStr = typet.Length[str]
    with pytest.raises(TypeError):
        LengthBoundedStr = typet.Length[str, 10:20, lambda x: x]
    LengthBoundedStr = typet.Length[str, 1:5]
    with pytest.raises(ValueError):
        LengthBoundedStr("")
    assert LengthBoundedStr("a") == "a"
    assert LengthBoundedStr("abcde") == "abcde"
    with pytest.raises(ValueError):
        LengthBoundedStr("abcdef")
    LengthBoundedList = typet.Length[list, 1:1]
    with pytest.raises(ValueError):
        LengthBoundedList([])
    assert LengthBoundedList([1]) == [1]
    with pytest.raises(ValueError):
        LengthBoundedList([1, 2])
    assert str(LengthBoundedStr) == "typet.validation.Length[str, 1:5]"
    assert typet.Length[Any, 1:5]("abc") == "abc"
    assert typet.Length["str", 20]("abc") == "abc"


def test_string_type():
    """Test the bounded string type object."""
    with pytest.raises(TypeError):
        BoundedStr = typet.String[10:20, lambda x: x]
    BoundedStr = typet.String[1:5]
    with pytest.raises(ValueError):
        BoundedStr("")
    assert BoundedStr("a") == "a"
    assert BoundedStr("abcde") == "abcde"
    with pytest.raises(ValueError):
        BoundedStr("abcdef")
    assert str(BoundedStr) == "typet.validation.String[1:5]"
    assert typet.String("hello") == "hello"


def test_validation_type():
    """Test that the validation type validates content."""
    ValidFile = typet.Valid[os.path.isfile]
    assert ValidFile(__file__) == __file__
    with pytest.raises(TypeError):
        typet.Valid[int, int, int]


def test_path_types():
    """Test that the supplied path validation paths work."""
    assert str(typet.File(__file__)) == __file__
    with pytest.raises(ValueError):
        typet.File(str(uuid.uuid4()))
    assert str(typet.Dir(os.path.dirname(__file__))) == os.path.dirname(
        __file__
    )
    with pytest.raises(ValueError):
        typet.Dir(str(uuid.uuid4()))
    assert str(typet.ExistingPath(__file__)) == __file__
    assert str(
        typet.ExistingPath(os.path.dirname(__file__))
    ) == os.path.dirname(__file__)
    with pytest.raises(ValueError):
        typet.ExistingPath(str(uuid.uuid4()))


def test_none_type():
    """Verify that NoneType is type(None)."""
    assert typet.NoneType is type(None)


def test_singleton():
    """Test that a singleton only allows a single instance of a class."""

    @six.add_metaclass(typet.Singleton)
    class TestClass(object):
        pass

    assert TestClass() is TestClass()


def test_uninstantiable():
    """Test that an uninstantiable class cannot be instantiated."""

    @six.add_metaclass(typet.Uninstantiable)
    class TestClass(object):
        pass

    with pytest.raises(TypeError):
        TestClass()


def test_isinstance():
    """Test that instances of sliced type are instances of validation type."""
    Age = typet.Bounded[int, 0:150]
    assert isinstance(25, Age) is True
    assert isinstance(-5, Age) is False
    assert isinstance(200, Age) is False
    assert isinstance("not an int", Age) is False


def test_strict_object():
    """Simple test to verify basic StrictObject functionality."""

    class X(typet.StrictObject):
        x = None  # type: str

    x = X("initial")
    x.x = "hello"
    assert is_instance(x.x, str)
    assert x.x == "hello"
    with pytest.raises(TypeError):
        x.x = 5


def test_object():
    """Simple test to verify basic Object functionality."""

    class X(typet.Object):
        x = None  # type: Optional[str]

    x = X()
    x.x = 5
    assert is_instance(x.x, str)
    assert x.x == "5"


def test_object_with_default():
    """Test that Object uses a default value."""

    class X(typet.Object):
        x = 5  # type: Optional[int]

    x = X()
    assert x.x == 5


def test_object_comments():
    """Simple test to verify basic Object functionality with comment hints."""

    class X(typet.Object):
        x = None  # type: str

    with pytest.raises(TypeError):
        X()
    x = X(5)
    assert is_instance(x.x, str)
    assert x.x == "5"


def test_object_failure():
    """Simple test to verify basic Object failure functionality."""

    class X(typet.Object):
        x = None  # type: Optional[int]

    x = X()
    x.x = None
    with pytest.raises(TypeError):
        x.x = "not an integer"
