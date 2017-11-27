# -*- coding: utf-8 -*-
"""A module containing base objects for creating typed classes.

Classes:
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
import re
import tokenize
import types

import six
from typingplus import (  # noqa: F401 pylint: disable=unused-import
    cast,
    get_type_hints,
    is_instance,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
)

from .types import NoneType  # pylint: disable=redefined-builtin


__all__ = (
    'BaseStrictObject',
    'StrictObject',
    'BaseObject',
    'Object'
)


_T = TypeVar('_T')


def _get_type_name(type_):
    # type: (type) -> str
    """Return a displayable name for the type.

    Args:
        type_: A class object.

    Returns:
        A string value describing the class name that can be used in a natural
        language sentence.
    """
    name = repr(type_)
    if name.startswith('<'):
        name = getattr(type_, '__qualname__', getattr(type_, '__name__', ''))
    return name.rsplit('.', 1)[-1] or repr(type_)


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
            for token, value, _, _, _ in tokens:  # type: ignore
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


def _is_propertyable(names,  # type: List[str]
                     attrs,  # type: Dict[str, Any]
                     annotations,  # type: Dict[str, type]
                     attr  # Dict[str, Any]
                     ):
    # type: (...) -> bool
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
    # type: (Callable[[str, str, Type[_T]], Callable[[_T], None]]) -> type
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
        # type: (str, str, Type[_T]) -> Callable[[], Any]
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
            # type: (...) -> Any
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

        def __new__(mcs,  # type: Type[_AnnotatedObjectMeta]
                    name,  # type: str
                    bases,  # type: List[type]
                    attrs  # type: Dict[str, Any]
                    ):
            # type: (...) -> type
            """Create class objs that replaces annotated attrs with properties.

            Args:
                mcs: The class object being created.
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
                attrs[attr] is None and use_comment_type_hints and
                NoneType in getattr(annotations[attr], '__args__', ())
            ]
            return super(_AnnotatedObjectMeta, mcs).__new__(
                mcs, name, bases, typed_attrs)

    return _AnnotatedObjectMeta


def _strict_object_meta_fset(_, private_attr, type_):
    # type: (str, str, Type[_T]) -> Callable[[_T], None]
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
    def _fset(self,
              value  # type: Any
              ):
        # type: (...) -> None
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


_StrictObjectMeta = _create_typed_object_meta(_strict_object_meta_fset)


def _object_meta_fset(_, private_attr, type_):
    # type: (str, str, Type[_T]) -> Callable[[_T], None]
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
    def _fset(self,
              value  # type: Any
              ):
        # type: (...) -> None
        """Set the value on self and coerce it to type_ if necessary.

        Args:
            value: The value to set.

        Raises:
            TypeError: Raised when the value is not an instance of type_
                and cannot be cast into a compatible object of type_.
        """
        return setattr(self, private_attr, cast(type_, value))

    return _fset


_ObjectMeta = _create_typed_object_meta(_object_meta_fset)


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
        # type: () -> str
        """Return a Python readable representation of the class."""
        return '{}({})'.format(
            self.__class__.__name__,
            ', '.join(
                '{}={}'.format(attr_name, repr(getattr(self, attr_name)))
                for attr_name in
                self.__class__._tp__typed_properties))  # type: ignore


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


@six.add_metaclass(_StrictObjectMeta)  # type: ignore
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


@six.add_metaclass(_ObjectMeta)  # type: ignore
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
