Type[T]
=======

|PyPI| |Python Versions| |Build Status| |Coverage Status| |Code Quality|

*Types that make coding in Python quick and safe.*

Type[T] works best with Python 3.6 or later. Prior to 3.6, object types must
use comment type hint syntax.


Installation
------------

Install it using pip:

::

    pip install typet


Features
--------

- An Object base class that eliminates boilerplate code and verifies and
  coerces types when possible.
- Validation types that, when instantiated, create an instance of a specific
  type and verify that they are within the user defined boundaries for the
  type.


Quick Start: Creating a `Person`
--------------------------------

Import the Type[T] types that you will use.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from typet import Bounded, Object, String

* `Object`, for composing complex objects
* `Bound` to describe a type that validates its value is of the correct type and within bounds upon instantiation
* `String`, which will validate that it is instantiated with a string with a length within the defined bounds.

Create Type Aliases That Describe the Intent of the Type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    Age = Bounded[int, 0:150]
    Name = String[1:50]
    Hobby = String[1:300]

In this example, a `Person` has an `Age`, which is an integer between 0 and
150, inclusive; a `Name` which must be a non-empty string with no more than
50 characters; and finally, a `Hobby`, which is a non-empty string with no more
than 300 characters.

Compose a `Person` object Using Type Aliases
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class Person(Object):
        name: Name
        surname: Name
        age: Age
        hobby: Hobby = None

Assigning a class attribute sets that value as the default value for instances
of the `Object`. In this instance, `hobby` is assigned a default value of
`None`; by convention, this tells Python that the type is `Optional[Hobby]`,
and Type[T] will allow `None` in addition to strings of the correct length.


Put It All Together
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from typet import Bounded, Object, String

    Age = Bounded[int, 0:150]
    Name = String[1:50]
    Hobby = String[1:300]

    class Person(Object):
        name: Name
        surname: Name
        age: Age
        hobby: Hobby = None

`Person` is now a clearly defined and typed object with an intuitive
constructor, hash method, comparison operators and bounds checking.

Positional arguments will be in the order of the definition of class
attributes, and keyword arguments are also acceptable.

.. code-block:: python

    jim = Person('Jim', 'Coder', 23, 'Python')
    bob = Person('Robert', 'Coder', hobby='C++', age=51)


Python 2.7 to 3.5
~~~~~~~~~~~~~~~~~

Type[T] supports PEP 484 class comment type hints for defining an `Object`.

.. code-block:: python

    from typing import Optional

    from typet import Bounded, Object, String

    Age = Bounded[int, 0:150]
    Name = String[1:50]
    Hobby = String[1:300]

    class Person(Object):
        name = None  # type: Name
        surname = None  # type: Name
        age = None  # type: Age
        hobby = None  # type: Optional[Hobby]

Note that, because Python prior to 3.6 cannot annotate an attribute without
defining it, by convention, assigning the attribute to `None` will not imply
that it is optional; it must be specified explicitly in the type hint comment.


`Object` Types
--------------

`Object`
~~~~~~~~

One of the cooler features of Type[T] is the ability to create complex
objects with very little code. The following code creates an object that
generates properties from the annotated class attributes that will ensure that
only values of *int* or that can be coerced into *int* can be set. It also
generates a full suite of common comparison methods.

.. code-block:: python

    from typet import Object

    class Point(Object):
        x: int
        y: int

Point objects can be used intuitively because they generate a standard
`__init__` method that will allow positional and keyword arguments.

.. code-block:: python

    p1 = Point(0, 0)      # Point(x=0, y=0)
    p2 = Point('2', 2.5)  # Point(x=2, y=2)
    p3 = Point(y=5, x=2)  # Point(x=2, y=5)
    assert p1 < p2        # True
    assert p2 < p1        # AssertionError


A close equivalent traditional class would be much larger, would have to be
updated for any new attributes, and wouldn't support more advanced casting,
such as to types annotated using the typing_ module:

.. code-block:: python

    class Point(object):

        def __init__(self, x, y):
            self.x = x
            self.y = y

        def __repr__(self):
            return 'Point(x={x}, y={y})'.format(x=self.x, y=self.y)

        def __setattr__(self, name, value):
            if name in ('x', 'y'):
                value = int(value)
            super(Point, self).__setattr__(name, value)

        def __eq__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return (self.x, self.y) == (other.x, other.y)

        def __ne__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return (self.x, self.y) != (other.x, other.y)

        def __lt__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return (self.x, self.y) < (other.x, other.y)

        def __le__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return (self.x, self.y) <= (other.x, other.y)

        def __gt__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return (self.x, self.y) > (other.x, other.y)

        def __ge__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return (self.x, self.y) >= (other.x, other.y)

        def __hash__(self):
            return hash((self.x, self.y))


Attributes can be declared optional either manually, by using typing.Optional_
or by using the PEP 484 implicit optional of a default value of `None`.

.. code-block:: python

    from typing import Optional

    from typet import Object

    class Point(Object):
        x: Optional[int]
        y: int = None

    p1 = Point()   # Point(x=None, y=None)
    p2 = Point(5)  # Point(x=5, y=None)


`StrictObject`
~~~~~~~~~~~~~~

By default, `Object` will use `cast` from typingplus_ to attempt to coerce
any values supplied to attributes to the annotated type. In some cases, it may
be preferred to disallow casting and only allow types that are already of the
correct type. `StrictObject` has all of the features of `Object`, but will not
coerce values into the annotated type.

.. code-block:: python

    from typet import StrictObject

    class Point(StrictObject):
        x: int
        y: int

    Point(0, 0)      # Okay
    Point('2', 2.5)  # Raises TypeError

`StrictObject` uses `is_instance` from typingplus_ to check types, so it's
possible to use types from the typing_ library for stricter checking.

.. code-block:: python

    from typing import List

    from typet import StrictObject

    class IntegerContainer(StrictObject):
        integers: List[int]

    IntegerContainer([0, 1, 2, 3])          # Okay
    IntegerContainer(['a', 'b', 'c', 'd'])  # Raises TypeError


Validation Types
----------------

Type[T] contains a suite of sliceable classes that will create bounded, or
validated, versions of those types that always assert their values are within
bounds; however, when an instance of a bounded type is instantiated, the
instance will be of the original type.

`Bounded`
~~~~~~~~~

`Bounded` can be sliced with either two arguments or three. The first argument
is the type being bound. The second is a `slice` containing the upper and lower
bounds used for comparison during instantiation.

.. code-block:: python

    from typet import Bounded

    BoundedInt = Bounded[int, 10:20]

    BoundedInt(15)  # Okay
    type(x)         # <class 'int'>
    BoundedInt(5)   # Raises ValueError

Optionally, a third argument, a function, may be supplied that will be run on
the value before the comparison.

.. code-block:: python

    from typet import Bounded

    LengthBoundedString = Bounded[str, 1:3, len]

    LengthBoundedString('ab')    # Okay
    LengthBoundedString('')      # Raises ValueError
    LengthBoundedString('abcd')  # Raises ValueError


`Length`
~~~~~~~~

Because `len` is a common comparison method, there is a shortcut type, `Length`
that takes two arguments and uses `len` as the comparison method.

.. code-block:: python

    from typing import List

    from typet import Length

    LengthBoundedList = Length[List[int], 1:3]

    LengthBoundedList([1, 2])        # Okay
    LengthBoundedList([])            # Raises ValueError
    LengthBoundedList([1, 2, 3, 4])  # Raises ValueError


`String`
~~~~~~~~

`str` and `len` are commonly used together, so a special type, `String` has
been added to simplify binding strings to specific lengths.

.. code-block:: python

    from typet import String

    ShortString = String[1:3]

    ShortString('ab')    # Okay
    ShortString('')      # Raises ValueError
    ShortString('abcd')  # Raises ValueError

Note that, on Python 2, `String` instantiates `unicode` objects and not `str`.


.. _typingplus: https://github.com/contains-io/typingplus/
.. _typing: https://docs.python.org/3/library/typing.html
.. _typing.Optional: https://docs.python.org/3/library/typing.html#typing.Optional

.. |Build Status| image:: https://travis-ci.org/contains-io/typet.svg?branch=master
   :target: https://travis-ci.org/contains-io/typet
.. |Coverage Status| image:: https://coveralls.io/repos/github/contains-io/typet/badge.svg?branch=master
   :target: https://coveralls.io/github/contains-io/typet?branch=master
.. |PyPI| image:: https://img.shields.io/pypi/v/typet.svg
   :target: https://pypi.python.org/pypi/typet/
.. |Python Versions| image:: https://img.shields.io/pypi/pyversions/typet.svg
   :target: https://pypi.python.org/pypi/typet/
.. |Code Quality| image:: https://api.codacy.com/project/badge/Grade/dae19ee1767b492e8bdf5edb16409f65
   :target: https://www.codacy.com/app/contains-io/typet?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=contains-io/typet&amp;utm_campaign=Badge_Grade
