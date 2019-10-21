# -*- coding: utf-8 -*-
"""A module for handling with typing and type hints.

In addition to the functions below, it also exports everything that the typing
and typing_extensions modules export.

Functions:
    cast: Casts a value to a specific type.
    eval_type: Evaluates a type, or a string of the type.
    get_type_hints: Gets all type hints for an object, including comment type
        hints.
    is_instance: An implementation of isinstance that works with the type
        definitions from the typing library.
"""
# pragma pylint: disable=W0641,W0703

from typing import (
    _eval_type,
    _get_defaults,
    Any,
    ByteString,
    Iterable,
    Mapping,
    MutableSequence,
    Optional,
    TypeVar,
)
import collections
import functools
import inspect
import re
import sys
import tokenize
import types
import typing

import six

try:
    from typing import ForwardRef
except ImportError:
    from typing import _ForwardRef as ForwardRef


_get_type_hints = typing.get_type_hints

_STRING_TYPES = six.string_types + (ByteString, bytes, bytearray)

# Deque is not registered in some versions of the typing library.
MutableSequence.register(collections.deque)


def get_type_hints(obj,  # type: Any
                   globalns=None,  # type: Optional[Dict[str, Any]]
                   localns=None  # type: Optional[Dict[str, Any]]
                   ):
    # type: (...) -> Dict[str, Any]
    """Return all type hints for the function.

    This attempts to use typing.get_type_hints first, but if that returns None
    then it will attempt to reuse much of the logic from the Python 3 version
    of typing.get_type_hints; the Python 2 version does nothing. In addition to
    this logic, if no code annotations exist, it will attempt to extract
    comment type hints for Python 2/3 compatibility.

    Args:
        obj: The object to search for type hints.
        globalns: The currently known global namespace.
        localns: The currently known local namespace.

    Returns:
        A mapping of value names to type hints.
    """
    hints = {}
    try:
        if not isinstance(obj, type):
            hints = _get_type_hints(obj, globalns, localns) or {}
    except TypeError:
        if not isinstance(obj, _STRING_TYPES):
            raise
    if not hints and not getattr(obj, '__no_type_check__', None):
        globalns, localns = _get_namespace(obj, globalns, localns)
        hints = _get_comment_type_hints(obj, globalns, localns)
        for name, value in six.iteritems(hints):
            if value is None:
                value = type(None)
            elif isinstance(value, _STRING_TYPES):
                value = ForwardRef(value)
            hints[name] = _eval_type(value, globalns, localns)
    return hints


def _get_namespace(obj,  # type: Any
                   globalns,  # type: Optional[Dict[str, Any]]
                   localns  # type: Optional[Dict[str, Any]]
                   ):
    # type: (...) -> Tuple[Dict[str, Any], Dict[str, Any]]
    """Retrieve the global and local namespaces for an object.

    Args:
        obj: An object.
        globalns: The currently known global namespace.
        localns: The currently known local namespace.

    Returns:
        A tuple containing two dictionaries for the global and local namespaces
        to be used by eval.
    """
    if globalns is None:
        globalns = getattr(obj, '__globals__', {})
        if localns is None:
            localns = globalns
    elif localns is None:
        localns = globalns
    return globalns, localns


def _get_type_comments(source):
    # type: (str) -> Generator[Tuple[str, str, Any], None, None]
    """Yield type hint comments from the source code.

    Args:
        source: The source code of the function to search for type hint
            comments.

    Yields:
        All type comments that come before the body of the function as
        (name, type) pairs, where the name is the name of the variable and
        type is the type hint. If a short-form type hint is reached, it is
        yielded as a single string containing the entire type hint.
    """
    reader = six.StringIO(inspect.cleandoc(source)).readline
    name = last_token = None
    tokens = tokenize.generate_tokens(reader)
    is_func = source.startswith('def')
    indent_level = 0
    for token, value, _, _, _ in tokens:
        if is_func and token == tokenize.INDENT:
            return
        if token == tokenize.DEDENT:
            indent_level -= 1
        elif token == tokenize.NAME:
            if value in ('def', 'class'):
                indent_level += 1
            elif last_token != tokenize.OP:
                name = value
        elif token == tokenize.COMMENT and indent_level == 1:
            match = re.match(r'#\s*type:(.+)', value)
            if match:
                type_sig = match.group(1).strip()
                if '->' in type_sig and last_token == tokenize.NEWLINE:
                    name, type_sig = type_sig.split('->', 1)
                    yield name.strip(), type_sig.strip()
                elif name:
                    yield name.strip(), type_sig.strip()
                name = None
        last_token = token


def _get_comment_type_hints(obj,  # type: Any
                            globalns,  # type: Dict[str, Any]
                            localns  # type: Dict[str, Any]
                            ):
    # type: (...) -> Dict[str, Any]
    """Get a mapping of any names to type hints from type hint comments.

    Args:
        obj: The object to search for type hint comments.

    Returns:
        A dictionary mapping names to the type hints found in comments.
    """
    if isinstance(obj, (types.FunctionType, types.MethodType)):
        return _get_func_type_hints(obj, globalns, localns)
    if isinstance(obj, type):
        return _get_class_type_hints(obj, globalns, localns)
    if isinstance(obj, types.ModuleType):
        try:
            source = inspect.getsource(obj)
        except (IOError, TypeError):
            return {}
    else:
        source = obj
    hints = {}
    for name, value in _get_type_comments(source):
        hints[name] = value
    return hints


def _get_class_type_hints(type_,  # type: Type
                          globalns,  # type: Dict[str, Any]
                          localns  # type: Dict[str, Any]
                          ):
    # type: (...) -> Dict[str, Any]
    """Get a mapping of class attr names to type hints from type hint comments.

    Args:
        type_: The class object to search for type hint comments.

    Returns:
        A dictionary mapping the class attribute names to the type hints found
        for each class attribute in the type hint comments.
    """
    hints = {}
    for base in reversed(type_.__mro__):
        if globalns is None:
            try:
                base_globals = sys.modules[base.__module__].__dict__
            except KeyError:
                base_globals = globalns
        else:
            base_globals = globalns
        base_hints = vars(base).get('__annotations__', {})
        if not base_hints:
            try:
                source = inspect.getsource(base)
                ns = localns if base is type_ else {}
                base_hints = _get_comment_type_hints(source, base_globals, ns)
            except (IOError, TypeError):
                pass
        hints.update(base_hints)
    return hints


def _get_func_type_hints(func,  # type: Callable[..., Any]
                         globalns,  # type: Dict[str, Any]
                         localns  # type: Dict[str, Any]
                         ):
    # type: (...) -> Dict[str, Any]
    """Get a mapping of parameter names to type hints from type hint comments.

    Args:
        func: The function to search for type hint comments.

    Returns:
        A dictionary mapping the function parameters to the type hints found
        for each parameter in the type hint comments.
    """
    try:
        source = inspect.getsource(func)
    except (IOError, TypeError):
        return {}
    hints = {}
    getargspec = getattr(
        inspect, 'get{}argspec'.format('full' if six.PY3 else ''))
    full_signature = getargspec(func)
    signature = list(full_signature[0]) + [s for s in full_signature[1:3] if s]
    for comment in _get_type_comments(source):
        name, value = comment
        if name in signature:
            hints[name] = value
        elif name.startswith('(') and name.endswith(')'):
            hints['return'] = value
            type_values = _parse_short_form(name, globalns, localns)
            if len(type_values) == len(signature) - 1:
                signature = signature[1:]
            if len(type_values) == len(signature):
                hints.update(zip(signature, type_values))
    defaults = _get_func_defaults(func)
    for name, value in six.iteritems(hints):
        if name in defaults and defaults[name] is None:
            hints[name] = Optional[value]
    return hints


def _get_func_defaults(func):
    # type: (Callable[..., Any]) -> Dict[str, Any]
    """Get the default values for the function parameters.

    Args:
        func: The function to inspect.

    Returns:
        A mapping of parameter names to default values.
    """
    _func_like = functools.wraps(func)(lambda: None)
    _func_like.__defaults__ = getattr(func, '__defaults__', None)
    if hasattr(func, '__code__'):
        _func_like.__code__ = func.__code__
    if not hasattr(_func_like, '__kwdefaults__'):
        _func_like.__kwdefaults__ = {}
    return _get_defaults(_func_like)


def _parse_short_form(comment, globalns, localns):
    # type: (str, Dict[str, Any], Dict[str, Any]) -> Tuple[type, ...]
    """Return the hints from the comment.

    Parses the left-hand side of a type comment into a list of type objects.
    (e.g. everything to the left of "->").

    Returns:
        A list of types evaluated from the type comment in the given global
        name space.
    """
    if '(...)' in comment:
        return ()
    comment = comment.replace('*', '')
    hints = eval(comment, globalns, localns)  # pylint: disable=eval-used
    if not isinstance(hints, tuple):
        hints = (hints,)
    return hints


def cast(tp, obj):
    # type: (Type[_T], Any) -> _T
    """Cast the value to the given type.

    Args:
        tp: The type the value is expected to be cast.
        obj: The value to cast.

    Returns:
        The cast value if it was possible to determine the type and cast it.
    """
    if is_instance(obj, tp):
        return obj
    type_repr = repr(tp)
    obj_repr = repr(obj)
    if tp in _STRING_TYPES:
        obj = _cast_string(tp, obj)
        if is_instance(obj, tp):
            return obj
    if (hasattr(tp, '__origin__') and
            tp.__origin__ or hasattr(tp, '__args__') and tp.__args__):
        obj = _cast_iterables(tp, obj)
    for type_ in _get_cast_types(tp):
        try:
            args = getattr(type_, '__args__', None)
            constraints = getattr(type_, '__constraints__', None)
            if args or constraints:
                return cast(type_, obj)
            return type_(obj)
        except Exception as e:  # NOQA
            pass
    six.raise_from(
        TypeError("Cannot convert {} to {}.".format(obj_repr, type_repr)),
        locals().get('e')
    )


def _get_cast_types(type_):
    # type: (Type) -> List[Union[type, Callable[..., Any]]]
    """Return all type callable type constraints for the given type.

    Args:
        type_: The type variable that may be callable or constrainted.

    Returns:
        A list of all callable type constraints for the type.
    """
    cast_types = [type_] if callable(
        type_) and type_.__module__ != 'typing' else []
    if (hasattr(type_, '__constraints__') and
            isinstance(type_.__constraints__, Iterable)):
        cast_types.extend(type_.__constraints__)
    if (hasattr(type_, '__args__') and
            isinstance(type_.__args__, Iterable) and
            not _is_subclass(type_, Mapping)):
        cast_types.extend(type_.__args__)
    if hasattr(type_, '_abc_registry'):
        cast_types.extend(sorted(  # Give list and tuple precedence.
            type_._abc_registry,
            key=lambda k: k.__name__,
            reverse=True))
    if hasattr(type_, '__extra__') and type_.__extra__:
        if isinstance(type_.__extra__, type):
            cast_types.append(type_.__extra__)
        if hasattr(type_.__extra__, '_abc_registry'):
            cast_types.extend(sorted(  # Give list and tuple precedence.
                type_.__extra__._abc_registry,
                key=lambda k: k.__name__,
                reverse=True))
    if hasattr(type_, '__origin__') and type_.__origin__:
        cast_types.append(type_.__origin__)
    try:
        type_name = vars(type_).get('_name')
        if type_name == 'MutableSequence':
            cast_types.insert(0, list)
        elif type_name == 'MutableSet':
            cast_types.insert(0, set)
    except TypeError:
        pass
    return cast_types


def is_instance(obj, type_):
    # type: (Any, Type) -> bool
    """Determine if an object is an instance of a type.

    In addition to the built-in isinstance, this method will compare against
    Any and TypeVars.

    Args:
        obj: Any object.
        type_: The type to check the object instance against.

    Returns:
        True if the object is an instance of the type; otherwise, False.
    """
    if type_ == Any or type_ is ByteString and isinstance(
            obj, (bytes, bytearray)):
        return True
    if isinstance(type_, type):
        if hasattr(type_, '__args__') and type_.__args__:
            generic_type = (type_.__origin__ if hasattr(
                type_, '__origin__') and type_.__origin__ else type_)
            if _is_subclass(type_, tuple) and Ellipsis not in type_.__args__:
                return (len(obj) == len(type_.__args__) and
                        isinstance(obj, generic_type) and all(
                            is_instance(val, typ) for typ, val in
                            zip(type_.__args__, obj)))
            if _is_subclass(type_, Mapping):
                return isinstance(obj, generic_type) and all(
                    is_instance(k, type_.__args__[0]) and
                    is_instance(v, type_.__args__[1]) for
                    k, v in six.iteritems(obj)
                )
            if _is_subclass(type_, Iterable):
                return isinstance(obj, generic_type) and all(
                    is_instance(v, type_.__args__[0]) for v in obj)
        elif isinstance(obj, type_):
            return True
    args = getattr(type_, '__args__', getattr(type_, '__constraints__', None))
    return any(is_instance(obj, typ) for typ in args or ())


def _cast_iterables(type_, obj):
    # type: (Type, Any) -> Any
    """Cast items contained in the object if the object is a container.

    Args:
        type_: The type of the container. If the object is not a container, no
            casting is performed.
        obj: The container object. If the object is not a container, no casting
            is performed.

    Returns:
        An object that can be cast to the given type. This may be either the
        original object, or a generator that casts all items within the object
        if the object is a container.
    """
    if not type_.__args__ or TypeVar in (type(t) for t in type_.__args__):
        return obj
    if _is_subclass(type_, tuple) and Ellipsis not in type_.__args__:
        if len(obj) == len(type_.__args__):
            return [cast(typ, val) for typ, val in zip(type_.__args__, obj)]
        raise TypeError(
            'The number of elements [{}] does not match the type {}'.format(
                len(obj), repr(type_)))
    if _is_subclass(type_, Mapping):
        return {
            cast(type_.__args__[0], k): cast(type_.__args__[1], v)
            for k, v in six.iteritems(obj)
        }
    if _is_subclass(type_, Iterable):
        return [cast(type_.__args__[0], v) for v in obj]
    return obj


def _cast_string(type_, obj):
    # type: (Type, Any) -> Any
    """Cast the object to a string type.

    If the type is a ByteString, but the object does not have a __bytes__
    method, the object will first be converted to a string.

    Note:
        This does not guarantee that it will cast to a string, as some aspects
        are assumed to be handled by the calling function. Unless the object
        needs to be encoded or decoded, the object will be returned unmodified.

    Args:
        type_: The type to cast the object to if possible.
        obj: The object to cast.

    Returns:
        The object cast to a string type if necessary. This is only necessary
        if the requested type is a ByteString and the object does not have a
        __bytes__ method, or the object needs to be encoded or decoded.
    """
    encoding = sys.stdin.encoding or sys.getdefaultencoding()
    if _is_subclass(type_, ByteString):
        if not hasattr(obj, '__bytes__'):
            obj = str(obj)
        if isinstance(obj, six.string_types):
            bytestr = obj.encode(encoding)
            if _is_subclass(type_, bytearray):
                return bytearray(bytestr)
            return bytestr
    if _is_subclass(type_, six.string_types) and isinstance(obj, ByteString):
        return obj.decode(encoding)
    return obj


def _is_subclass(type_, class_or_tuple):
    # type: (Type, Union[Type, Tuple]) -> bool
    """Determine if the type is a subclass of the given class or classes.

    This takes __origin__ classes into consideration and does not raise.

    Args:
        type_: The type that may be a subclass.
        class_or_tuple: A type or a tuple containing multiple types of which
            type_ may be a subclass.

    Returns:
        A boolean indicating whether the given type is a subclass of the
    """
    try:
        return issubclass(type_, class_or_tuple)
    except (TypeError, AttributeError):
        pass
    if hasattr(type_, '__origin__') and type_.__origin__:
        try:
            return issubclass(type_.__origin__, class_or_tuple)
        except (TypeError, AttributeError):
            pass
    return False


def eval_type(type_, globalns=None, localns=None):
    """Evaluate the type. If the type is string, evaluate it with ForwardRef.

    Args:
        type_: The type to evaluate.
        globalns: The currently known global namespace.
        localns: The currently known local namespace.

    Returns:
        The evaluated type.
    """
    globalns, localns = _get_namespace(type_, globalns, localns)
    if isinstance(type_, six.string_types):
        type_ = ForwardRef(type_)
    return _eval_type(type_, globalns, localns)
