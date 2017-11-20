# -*- coding: utf-8 -*-
# pragma pylint: disable=bad-mcs-classmethod-argument,too-many-lines
"""A module for handling with typing and type hints.

Classes:
    Bounded: A sliceable subclass of any class that raises a ValueError if the
        initialization value is out of bounds.
    Length: A sliceable subclass of any class that implements __len__ that
        raises a ValueError if the length of the initialization value is out of
        bounds.
    Singleton: A metaclass to force a class to only ever be instantiated once.
    DefType: A union of function and method types.
    NoneType: An alias for type(None)
    Valid: A sliceable type that validates any assigned value against a
        validation function.
    File: A type instance of Valid that validates that the value is a file.
    Dir: A type instance of Valid that validates that the value is a directory.
    Path: A type instance of Valid that expands a value to a path.
    BaseStrictObject: An object that asserts all annotated attributes are of
        the correct type.
    StrictObject: A derivative of BaseStrictObject that implements the default
        comparison operators and hash.
    BaseObject: An object that coerces all annotated attributes to the
        correct type.
    Object: A derivative of BaseObject that implements the default
        comparison operators and hash.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

import inspect
import os.path
import re
import tokenize
import types

import six
from typingplus import (  # noqa: F401 pylint: disable=unused-import
    _ForwardRef,
    cast,
    get_type_hints,
    is_instance,
    Any,
    Callable,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union
)

__all__ = (
    'Bounded',
    'Length',
    'Singleton',
    'DefType',
    'NoneType',
    'Valid',
    'File',
    'Dir',
    'Path',
    'BaseStrictObject',
    'StrictObject',
    'BaseObject',
    'Object'
)


_T = TypeVar('_T')

DefType = Union[types.FunctionType, types.MethodType]
NoneType = type(None)


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


class _ClsReprMeta(type):
    """A metaclass that returns a custom type repr if defined."""

    __class_repr__ = None  # type: Optional[str]

    def __repr__(cls):
        # type: () -> str
        """Return a custom string for the type repr if defined."""
        if cls.__class_repr__:
            return cls.__class_repr__
        return super(_ClsReprMeta, cls).__repr__()


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

        @six.add_metaclass(MetaClass)
        class _BoundedSubclass(BaseClass):
            """A subclass of type_ or object, bounded by a slice."""

            def __new__(cls, __value, *args, **kwargs):
                # type: (Any, *Any, **Any) -> _T
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
        """Get the base and meta classes to use in creating a subclass.

        Args:
            type_: The type to subclass.

        Returns:
            A tuple containing two values: a base class, and a metaclass.
        """
        try:
            class _(type_):
                """Check if type_ is subclassable."""
            BaseClass = type_
        except TypeError:
            BaseClass = object

        class MetaClass(_ClsReprMeta, BaseClass.__class__):
            """Use the type_ metaclass and include class repr functionality."""

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
        if isinstance(type_, six.string_types):
            type_ = _ForwardRef(type_)._eval_type(globals(), globals())
        return type_, bound, keyfunc

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
        # type: (_T) -> _T
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
        # type: (tuple) -> Tuple[Type[_T], slice, Callable]
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
        # type: (tuple) -> Tuple[Type[_T], slice, Callable]
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


def _expand_path(path):
    """Expand the path with user and environment variables.

    Args:
        path: The path to expand.

    Returns:
        The real path expanded with user and environment variables.
    """
    return os.path.realpath(os.path.expanduser(os.path.expandvars(path)))


Dir = Valid[_expand_path, os.path.isdir]
Dir.__class_repr__ = '{}.{}'.format(Dir.__module__, 'Dir')

File = Valid[_expand_path, os.path.isfile]
File.__class_repr__ = '{}.{}'.format(File.__module__, 'File')

Path = Valid[_expand_path, lambda v: v]
Path.__class_repr__ = '{}.{}'.format(Path.__module__, 'Path')

ExistingPath = Valid[_expand_path, os.path.exists]
ExistingPath.__class_repr__ = '{}.{}'.format(
    ExistingPath.__module__, 'ExistingPath')


def _get_type_name(type_):
    """Return a displayable name for the type.

    Args:
        type_: A class object.

    Returns:
        A string value describing the class name that can be used in a natural
        language sentence.
    """
    name = getattr(type_, '__qualname__', getattr(type_, '__name__', ''))
    return name.rsplit('.', 1)[-1] or str(type_)


def _get_class_frame_source(class_name):
    # type: (str) -> Optional[str]
    """Return the source code for a class by checking the frame stack.

    This is necessary because it is not possible to get the source of a class
    being created by a metaclass directly.

    Args:
        class_name: The class to look for on the stack.

    Returns:
        The source code for the requested class if the class was found and the
        source was accessible.
    """
    for frame_info in inspect.stack():
        with open(frame_info.filename) as fp:
            src = ''.join(
                fp.readlines()[frame_info.lineno - 1:])
        if re.search(r'class\s+{}'.format(class_name), src):
            reader = six.StringIO(src).readline
            tokens = tokenize.generate_tokens(reader)
            source_tokens = []
            indent_level = 0
            base_indent_level = 0
            has_base_level = False
            for token, value, _, _, _ in tokens:
                source_tokens.append((token, value))
                if token == tokenize.INDENT:
                    indent_level += 1
                elif token == tokenize.DEDENT:
                    indent_level -= 1
                    if has_base_level and indent_level <= base_indent_level:
                        return tokenize.untokenize(source_tokens)
                elif not has_base_level:
                    has_base_level = True
                    base_indent_level = indent_level


def _is_propertyable(names, attrs, annotations, attr):
    """Determine if an attribute can be replaced with a property.

    Args:
        names: The complete list of all attribute names for the class.
        attrs: The attribute dict returned by __prepare__.
        annotations: A mapping of all defined annotations for the class.
        attr: The attribute to test.

    Returns:
        True if the attribute can be replaced with a property; else False.
    """
    return (attr in annotations and
            not attr.startswith('_') and
            not attr.isupper() and
            '__{}'.format(attr) not in names and
            not isinstance(getattr(attrs, attr, None), types.MethodType))


def _create_typed_object_meta(get_fset):
    """Create a metaclass for typed objects.

    Args:
        get_fset: A function that takes three parameters: the name of an
            attribute, the name of the private attribute that holds the
            property data, and a type. This function must an object method that
            accepts a value.

    Returns:
        A metaclass that reads annotations from a class definition and creates
        properties for annotated, public, non-constant, non-method attributes
        that will guarantee the type of the stored value matches the
        annotation.
    """
    def _get_fget(attr, private_attr, type_):
        """Create a property getter method for an attribute.

        Args:
            attr: The name of the attribute that will be retrieved.
            private_attr: The name of the attribute that will store any data
                related to the attribute.
            type_: The annotated type defining what values can be stored in the
                attribute.

        Returns:
            A function that takes self and retrieves the private attribute from
            self.
        """
        def _fget(self):
            """Get attribute from self without revealing the private name."""
            try:
                return getattr(self, private_attr)
            except AttributeError:
                raise AttributeError(
                    "'{}' object has no attribute '{}'".format(
                        _get_type_name(type_), attr))

        return _fget

    class _AnnotatedObjectMeta(type):
        """A metaclass that reads annotations from a class definition."""

        def __new__(cls, name, bases, attrs):
            """Create class objs that replaces annotated attrs with properties.

            Args:
                cls: The class object being created.
                name: The name of the class to create.
                bases: The list of all base classes for the new class.
                attrs: The list of all attributes for the new class from the
                    definition.

            Returns:
                A new class instance with the expected base classes and
                attributes, but with annotated, public, non-constant,
                non-method attributes replaced by property objects that
                validate against the annotated type.
            """
            annotations = attrs.get('__annotations__', {})
            use_comment_type_hints = (
                not annotations and attrs.get('__module__') != __name__)
            if use_comment_type_hints:
                source = _get_class_frame_source(name)
                annotations = get_type_hints(source)
            names = list(attrs) + list(annotations)
            typed_attrs = {}
            for attr in names:
                typed_attrs[attr] = attrs.get(attr)
                if _is_propertyable(names, attrs, annotations, attr):
                    private_attr = '__{}'.format(attr)
                    if attr in attrs:
                        typed_attrs[private_attr] = attrs[attr]
                    type_ = (
                        Optional[annotations[attr]] if
                        not use_comment_type_hints and
                        attr in attrs and
                        attrs[attr] is None
                        else annotations[attr]
                    )
                    typed_attrs[attr] = property(
                        _get_fget(attr, private_attr, type_),
                        get_fset(attr, private_attr, type_)
                    )
            properties = [attr for attr in annotations if _is_propertyable(
                          names, attrs, annotations, attr)]
            typed_attrs['_tp__typed_properties'] = properties
            typed_attrs['_tp__undefined_typed_properties'] = [
                attr for attr in properties if attr not in attrs or
                attrs[attr] is None and use_comment_type_hints]
            return super(_AnnotatedObjectMeta, cls).__new__(
                cls, name, bases, typed_attrs)

    return _AnnotatedObjectMeta


@_create_typed_object_meta
def _StrictObjectMeta(_, private_attr, type_):
    """Create a property setter method for the attribute.

    Args:
        _: The name of the attribute to set. Unused.
        private_attr: The name of the attribute that will store any data
            related to the attribute.
        type_: The annotated type defining what values can be stored in the
            attribute.

    Returns:
        A method that takes self and a value and stores that value on self
        in the private attribute iff the value is an instance of type_.
    """
    def _fset(self, value):
        """Set the value on self iff the value is an instance of type_.

        Args:
            value: The value to set.

        Raises:
            TypeError: Raised when the value is not an instance of type_.
        """
        if not is_instance(value, type_):
            raise TypeError(
                'Cannot assign value of type {} to attribute of type {}.'
                .format(
                    _get_type_name(type(value)),
                    _get_type_name(type_)))
        return setattr(self, private_attr, value)

    return _fset


@_create_typed_object_meta
def _ObjectMeta(_, private_attr, type_):
    """Create a property setter method for the attribute.

    Args:
        _: The name of the attribute to set. Unused.
        private_attr: The name of the attribute that will store any data
            related to the attribute.
        type_: The annotated type defining what values can be stored in the
            attribute.

    Returns:
        A method that takes self and a value and stores that value on self
        in the private attribute if the value is not an instance of type_
        and cannot be cast into type_.
    """
    def _fset(self, value):
        """Set the value on self and coerce it to type_ if necessary.

        Args:
            value: The value to set.

        Raises:
            TypeError: Raised when the value is not an instance of type_
                and cannot be cast into a compatible object of type_.
        """
        return setattr(self, private_attr, cast(type_, value))

    return _fset


class _BaseAnnotatedObject(object):
    """A base class that looks for class attributes to create __init__."""

    def __init__(self, *args, **kwargs):
        """Set all attributes according to their annotation status."""
        super(_BaseAnnotatedObject, self).__init__()
        properties = self.__class__._tp__typed_properties
        required = self.__class__._tp__undefined_typed_properties
        positionals = zip(properties, args)
        for attr, value in positionals:
            if attr in kwargs:
                raise TypeError(
                    "__init__() got multiple values for argument '{}'"
                    .format(attr))
            kwargs[attr] = value
        missing = [attr for attr in required if attr not in kwargs]
        if missing:
            num_missing = len(missing)
            if num_missing > 1:
                args = ', '.join("'{}'".format(m) for m in missing[:-1])
                if num_missing > 2:
                    args += ','
                args += " and '{}'".format(missing[-1])
            else:
                args = "'{}'".format(missing[0])
            raise TypeError(
                '__init__() missing {} required argument{}: {}'.format(
                    num_missing, 's' if num_missing > 1 else '', args))
        for attr, value in six.iteritems(kwargs):
            if attr in properties:
                setattr(self, attr, value)

    def __repr__(self):
        """Return a Python readable representation of the class."""
        return '{}({})'.format(
            self.__class__.__name__,
            ', '.join(
                '{}={}'.format(attr_name, repr(getattr(self, attr_name)))
                for attr_name in self.__class__._tp__typed_properties))


class _AnnotatedObjectComparisonMixin(object):
    """A mixin to add comparisons to classes made by _AnnotatedObjectMeta."""

    def _tp__get_typed_properties(self):
        """Return a tuple of typed attrs that can be used for comparisons.

        Raises:
            NotImplementedError: Raised if this class was mixed into a class
                that was not created by _AnnotatedObjectMeta.
        """
        try:
            return tuple(getattr(self, p) for p in
                         self.__class__._tp__typed_properties)
        except AttributeError:
            raise NotImplementedError

    def __eq__(self, other):
        """Test if two objects of the same base class are equal.

        If the objects are not of the same class, Python will default to
        comparison-by-ID.

        Args:
            other: The object to compare for equality.

        Returns:
            True if the objects are equal; else False.
        """
        if other.__class__ is not self.__class__:
            return NotImplemented
        return (self._tp__get_typed_properties() ==
                other._tp__get_typed_properties())

    def __ne__(self, other):
        """Test if two objects of the same class are not equal.

        If the objects are not of the same class, Python will default to
        comparison-by-ID.

        Args:
            other: The object to compare for non-equality.

        Returns:
            True if the objects are not equal; else False.
        """
        if other.__class__ is not self.__class__:
            return NotImplemented
        return not self == other

    def __lt__(self, other):
        """Test if self is less than an object of the same class.

        Args:
            other: The object to compare against.

        Returns:
            True if self is less than other; else False.

        Raises:
            TypeError: Raised if the objects are not of the same class.
        """
        if other.__class__ is not self.__class__:
            return NotImplemented
        return (self._tp__get_typed_properties() <
                other._tp__get_typed_properties())

    def __le__(self, other):
        """Test if self is less than or equal an object of the same class.

        Args:
            other: The object to compare against.

        Returns:
            True if self is less than or equal other; else False.

        Raises:
            TypeError: Raised if the objects are not of the same class.
        """
        if other.__class__ is not self.__class__:
            return NotImplemented
        return self == other or self < other

    def __gt__(self, other):
        """Test if self is greater than an object of the same class.

        Args:
            other: The object to compare against.

        Returns:
            True if self is greater than other; else False.

        Raises:
            TypeError: Raised if the objects are not of the same class.
        """
        if other.__class__ is not self.__class__:
            return NotImplemented
        return not self <= other

    def __ge__(self, other):
        """Test if self is greater than or equal an object of the same class.

        Args:
            other: The object to compare against.

        Returns:
            True if self is greater than or equal to other; else False.

        Raises:
            TypeError: Raised if the objects are not of the same class.
        """
        if other.__class__ is not self.__class__:
            return NotImplemented
        return not self < other

    def __hash__(self):
        """Generate a hash for the object based on the annotated attrs."""
        return hash(self._tp__get_typed_properties())


@six.add_metaclass(_StrictObjectMeta)
class BaseStrictObject(_BaseAnnotatedObject):
    """A base class to create instance attrs for annotated class attrs.

    For every class attribute that is annotated, public, and not constant in
    the subclasses, this base class will generate property objects for the
    the instances that will enforce the type of the value set.

    If the subclass does not define __init__, a default implementation will be
    generated that takes all of the annotated, public, non-constant attributes
    as parameters. If an annotated attribute is not defined, it will be
    required in __init__.

    >>> from typet import BaseStrictObject
    >>> class Point(BaseStrictObject):
    ...     x: int
    ...     y: int
    ...
    ...
    >>> p = Point(0, 0)
    >>> p.x
    0
    >>> p.x = '0'
    Traceback (most recent call last):
        ...
    TypeError: Cannot assign value of type str to attribute of type int.
    """


class StrictObject(BaseStrictObject, _AnnotatedObjectComparisonMixin):
    """A base class to create instance attrs for annotated class attrs.

    For every class attribute that is annotated, public, and not constant in
    the subclasses, this base class will generate property objects for the
    the instances that will enforce the type of the value set.

    If the subclass does not define __init__, a default implementation will be
    generated that takes all of the annotated, public, non-constant attributes
    as parameters. If an annotated attribute is not defined, it will be
    required in __init__.

    >>> from typet import StrictObject
    >>> class Point(StrictObject):
    ...     x: int
    ...     y: int
    ...
    ...
    >>> p = Point(0, 0)
    >>> p.x
    0
    >>> p.x = '0'
    Traceback (most recent call last):
        ...
    TypeError: Cannot assign value of type str to attribute of type int.
    >>> p2 = Point(2, 2)
    >>> p < p2
    True
    >>> p > p2
    False
    """


@six.add_metaclass(_ObjectMeta)
class BaseObject(_BaseAnnotatedObject):
    """A base class to create instance attrs for annotated class attrs.

    For every class attribute that is annotated, public, and not constant in
    the subclasses, this base class will generate property objects for the
    the instances that will enforce the type of the value set by attempting to
    cast the given value to the set type.

    If the subclass does not define __init__, a default implementation will be
    generated that takes all of the annotated, public, non-constant attributes
    as parameters. If an annotated attribute is not defined, it will be
    required in __init__.

    Additionally, this class implements basic comparison operators and the hash
    function.

    >>> from typet import BaseObject
    >>> class Point(BaseObject):
    ...     x: int
    ...     y: int
    ...
    ...
    >>> p = Point(0, 0)
    >>> p.x
    0
    >>> p.x = '5'
    >>> p.x
    5
    >>> p.x = 'five'
    Traceback (most recent call last):
        ...
    TypeError: Cannot convert 'five' to int.
    """


class Object(BaseObject, _AnnotatedObjectComparisonMixin):
    """A base class to create instance attrs for annotated class attrs.

    For every class attribute that is annotated, public, and not constant in
    the subclasses, this base class will generate property objects for the
    the instances that will enforce the type of the value set by attempting to
    cast the given value to the set type.

    If the subclass does not define __init__, a default implementation will be
    generated that takes all of the annotated, public, non-constant attributes
    as parameters. If an annotated attribute is not defined, it will be
    required in __init__.

    Additionally, this class implements basic comparison operators and the hash
    function.

    >>> from typet import Object
    >>> class Point(Object):
    ...     x: int
    ...     y: int
    ...
    ...
    >>> p = Point(0, 0)
    >>> p.x
    0
    >>> p.x = '5'
    >>> p.x
    5
    >>> p.x = 'five'
    Traceback (most recent call last):
        ...
    TypeError: Cannot convert 'five' to int.
    >>> p2 = Point(2, 2)
    >>> p < p2
    True
    >>> p > p2
    False
    """
