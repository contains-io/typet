# -*- coding: utf-8 -*-
# pragma pylint: disable=bad-mcs-method-argument,bad-mcs-classmethod-argument
"""A module for handling with typing and type hints.

Classes:
    Bounded: A sliceable subclass of any class that raises a ValueError if the
        initialization value is out of bounds.
    Length: A sliceable subclass of any class that implements __len__ that
        raises a ValueError if the length of the initialization value is out of
        bounds.
    Valid: A sliceable type that validates any assigned value against a
        validation function.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

import six
from typingplus import (  # noqa: F401 pylint: disable=unused-import
    eval_type,
    Any,
    Callable,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union
)

from .meta import Uninstantiable


_T = TypeVar('_T')


class _ValidationMeta(type):
    """A metaclass that returns handles custom type checks."""

    __class_repr__ = None  # type: Optional[str]

    def __repr__(cls):
        # type: () -> str
        """Return a custom string for the type repr if defined."""
        if cls.__class_repr__:
            return cls.__class_repr__
        return super(_ValidationMeta, cls).__repr__()

    def __instancecheck__(cls, other):
        # type: (Any) -> bool
        try:
            cls(other)
            return True
        except ValueError:
            return False


class _BoundedMeta(Uninstantiable):
    """A metaclass that adds slicing to a class that creates new classes."""

    def __getitem__(cls, args):
        # type: (Union[Tuple[_T, Any], Tuple[_T, Any, Callable]]) -> type
        """Create a new subclass of a type bounded by the arguments.

        If a callable is passed as the third argument of the slice, it will be
        used as the comparison function for the boundaries.

        Args:
            args: A tuple with two or three parameters: a type, a slice
                representing the minimum and maximum lengths allowed for values
                of that type and, optionally, a function to use on values
                before comparing against the bounds.
        """
        type_, bound, keyfunc = cls._get_args(args)
        keyfunc_name = cls._get_fullname(keyfunc)
        identity = cls._identity
        BaseClass, MetaClass = cls._get_bases(type_)
        instantiate = cls._instantiate

        @six.add_metaclass(MetaClass)  # type: ignore
        class _BoundedSubclass(BaseClass):  # type: ignore
            """A subclass of type_ or object, bounded by a slice."""

            def __new__(cls, __value, *args, **kwargs):
                # type: (Type[_BoundedSubclass], Any, *Any, **Any) -> type
                """Return __value cast to _T.

                Any additional arguments are passed as-is to the constructor.

                Args:
                    __value: A value that can be converted to type _T.
                    args: Any additional positional arguments passed to the
                        constructor.
                    kwargs: Any additional keyword arguments passed to the
                        constructor.
                """
                instance = instantiate(
                    BaseClass, type_, __value, *args, **kwargs)
                cmp_val = keyfunc(instance)
                if bound.start is not None or bound.stop is not None:
                    if bound.start is not None and cmp_val < bound.start:
                        if keyfunc is not identity:
                            raise ValueError(
                                'The value of {}({}) [{}] is below the minimum'
                                ' allowed value of {}.'.format(
                                    keyfunc_name, repr(__value), repr(cmp_val),
                                    bound.start))
                        raise ValueError(
                            'The value {} is below the minimum allowed value '
                            'of {}.'.format(repr(__value), bound.start))
                    if bound.stop is not None and cmp_val > bound.stop:
                        if keyfunc is not identity:
                            raise ValueError(
                                'The value of {}({}) [{}] is above the maximum'
                                ' allowed value of {}.'.format(
                                    keyfunc_name, repr(__value), repr(cmp_val),
                                    bound.stop))
                        raise ValueError(
                            'The value {} is above the maximum allowed value '
                            'of {}.'.format(repr(__value), bound.stop))
                elif not cmp_val:
                    raise ValueError(
                        '{}({}) is False'.format(keyfunc_name, repr(instance)))
                return instance

        _BoundedSubclass.__class_repr__ = cls._get_class_repr(
            type_, bound, keyfunc, keyfunc_name)
        return _BoundedSubclass

    @staticmethod
    def _get_bases(type_):
        # type: (type) -> Tuple[type, type]
        """Get the base and meta classes to use in creating a subclass.

        Args:
            type_: The type to subclass.

        Returns:
            A tuple containing two values: a base class, and a metaclass.
        """
        try:
            class _(type_):  # type: ignore
                """Check if type_ is subclassable."""
            BaseClass = type_
        except TypeError:
            BaseClass = object

        class MetaClass(_ValidationMeta, BaseClass.__class__):  # type: ignore
            """Use the type_ meta and include base validation functionality."""

        return BaseClass, MetaClass

    @staticmethod
    def _instantiate(class_, type_, __value, *args, **kwargs):
        """Instantiate the object if possible.

        Args:
            class_: The class to instantiate.
            type_: The the class is uninstantiable, attempt to cast to a base
                type.
            __value: The value to return if the class and type are
                uninstantiable.
            *args: The positional arguments to pass to the class.
            **kwargs: The keyword arguments to pass to the class.

        Returns:
            The class or base type instantiated using the arguments. If it is
            not possible to instantiate either, returns __value.
        """
        try:
            return class_(__value, *args, **kwargs)
        except TypeError:
            try:
                return type_(__value, *args, **kwargs)
            except Exception:  # pylint: disable=broad-except
                return __value

    def _get_class_repr(cls, type_, bound, keyfunc, keyfunc_name):
        # type: (Any, slice, Callable, str) -> str
        """Return a class representation using the slice parameters.

        Args:
            type_: The type the class was sliced with.
            bound: The boundaries specified for the values of type_.
            keyfunc: The comparison function used to check the value
                boundaries.
            keyfunc_name: The name of keyfunc.

        Returns:
            A string representing the class.
        """
        if keyfunc is not cls._default:
            return '{}.{}[{}, {}, {}]'.format(
                cls.__module__, cls.__name__, cls._get_fullname(type_),
                cls._get_bound_repr(bound), keyfunc_name)
        return '{}.{}[{}, {}]'.format(
            cls.__module__, cls.__name__, cls._get_fullname(type_),
            cls._get_bound_repr(bound))

    def _get_args(cls, args):
        # type: (tuple) -> Tuple[Any, slice, Callable]
        """Return the parameters necessary to check type boundaries.

        Args:
            args: A tuple with two or three elements: a type, a slice
                representing the minimum and maximum lengths allowed for values
                of that type and, optionally, a function to use on values
                before comparing against the bounds.

        Returns:
            A tuple with three elements: a type, a slice, and a function to
            apply to objects of the given type. If no function was specified,
            it returns the identity function.
        """
        if not isinstance(args, tuple):
            raise TypeError(
                '{}[...] takes two or three arguments.'.format(cls.__name__))
        elif len(args) == 2:
            type_, bound = args
            keyfunc = cls._identity
        elif len(args) == 3:
            type_, bound, keyfunc = args
        else:
            raise TypeError(
                'Too many parameters given to {}[...]'.format(cls.__name__))
        if not isinstance(bound, slice):
            bound = slice(bound)
        return eval_type(type_), bound, keyfunc

    @staticmethod
    def _get_bound_repr(bound):
        # type: (slice) -> str
        """Return a string representation of a boundary slice.

        Args:
            bound: A slice object.

        Returns:
            A string representing the slice.
        """
        if bound.start is not None and bound.stop is None:
            return '{}:'.format(bound.start)
        if bound.stop is not None and bound.start is None:
            return ':{}'.format(bound.stop)
        return '{}:{}'.format(bound.start, bound.stop)

    @staticmethod
    def _identity(obj):
        # type: (Any) -> Any
        """Return the given object.

        Args:
            obj: An object.

        Returns:
            The given object.
        """
        return obj

    _default = _identity  # type: Callable[[Any], Any]

    @staticmethod
    def _get_fullname(obj):
        # type: (Any) -> str
        """Get the full name of an object including the module.

        Args:
            obj: An object.

        Returns:
            The full class name of the object.
        """
        if not hasattr(obj, '__name__'):
            obj = obj.__class__
        if obj.__module__ in ('builtins', '__builtin__'):
            return obj.__name__
        return '{}.{}'.format(obj.__module__, obj.__name__)


@six.add_metaclass(_BoundedMeta)
class Bounded(object):
    """A type that creates a bounded version of a type when sliced.

    Bounded can be sliced with two or three elements: a type, a slice
    representing the minimum and maximum lengths allowed for values of that
    type and, optionally, a function to use on values before comparing against
    the bounds.

    >>> Bounded[int, 5:10](7)
    7
    >>> Bounded[int, 5:10](1)
    Traceback (most recent call last):
        ...
    ValueError: The value 1 is below the minimum allowed value of 5.
    >>> Bounded[int, 5:10](11)
    Traceback (most recent call last):
        ...
    ValueError: The value 11 is above the maximum allowed value of 10.
    >>> Bounded[str, 5:10, len]('abcde')
    'abcde'
    """


class _LengthBoundedMeta(_BoundedMeta):
    """A metaclass that bounds a type with the len function."""

    _default = len

    def _get_args(cls, args):
        # type: (tuple) -> Tuple[type, slice, Callable]
        """Return the parameters necessary to check type boundaries.

        Args:
            args: A tuple with two parameters: a type, and a slice representing
                the minimum and maximum lengths allowed for values of that
                type.

        Returns:
            A tuple with three parameters: a type, a slice, and the len
            function.
        """
        if not isinstance(args, tuple) or not len(args) == 2:
            raise TypeError(
                '{}[...] takes exactly two arguments.'.format(cls.__name__))
        return super(_LengthBoundedMeta, cls)._get_args(args + (len,))


@six.add_metaclass(_LengthBoundedMeta)
class Length(object):
    """A type that creates a length bounded version of a type when sliced.

    Length can be sliced with two parameters: a type, and a slice representing
    the minimum and maximum lengths allowed for values of that type.

    >>> Length[str, 5:10]('abcde')
    'abcde'
    >>> Length[str, 5:10]('abc')
    Traceback (most recent call last):
        ...
    ValueError: The value of len('abc') [3] is below the minimum ...
    >>> Length[str, 5:10]('abcdefghijk')
    Traceback (most recent call last):
        ...
    ValueError: The value of len('abcdefghijk') [11] is above the maximum ...
    """


class _ValidationBoundedMeta(_BoundedMeta):
    """A metaclass that binds a type to a validation method."""

    def _get_args(cls, args):
        # type: (tuple) -> Tuple[type, slice, Callable]
        """Return the parameters necessary to check type boundaries.

        Args:
            args: A tuple with one or two parameters: A type to cast the
                value passed, and a predicate function to use for bounds
                checking.

        Returns:
            A tuple with three parameters: a type, a slice, and the predicate
            function. If no type was passed in args, the type defaults to Any.
        """
        if isinstance(args, tuple):
            if not len(args) == 2:
                raise TypeError(
                    '{}[...] takes one or two argument.'.format(cls.__name__))
            return super(_ValidationBoundedMeta, cls)._get_args(
                (args[0], None, args[1]))
        return super(_ValidationBoundedMeta, cls)._get_args((Any, None, args))

    def _get_class_repr(cls, type_, bound, keyfunc, keyfunc_name):
        # type: (Any, slice, Callable, str) -> str
        """Return a class representation using the slice parameters.

        Args:
            type_: The type the class was sliced with.
            bound: The boundaries specified for the values of type_.
            keyfunc: The comparison function used to check the value
                boundaries.
            keyfunc_name: The name of keyfunc.

        Returns:
            A string representing the class.
        """
        if type_ is not Any:
            return '{}.{}[{}, {}]'.format(
                cls.__module__, cls.__name__, cls._get_fullname(type_),
                keyfunc_name)
        return '{}.{}[{}]'.format(
            cls.__module__, cls.__name__, keyfunc_name)


@six.add_metaclass(_ValidationBoundedMeta)
class Valid(object):
    """A type that creates a type that is validated against a function.

    Valid can be sliced with one or two parameters: an optional type to cast
    the given value to, and a validation method.
    """
