typet
=====

|PyPI| |Python Versions| |Build Status| |Coverage Status| |Code Quality|

*Types that make validating types in Python easy.*

``typet`` works best with Python 3.6 or later. Prior to 3.6, object types must
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


Basic Usage
-----------

One of the cooler features of ``typet`` is the ability to create complex
objects with very little code. The following code creates an object that
generates properties from the annotated class attributes that will ensure that
only values of *int* or that can be coerced into *int* can be set. It also
generates a full suite of common comparison methods.

.. code-block:: python

    from typet import Object

    class Point(Object):
        x: int
        y: int

    p1 = Point(0, 0)      # Point(x=0, y=0)
    p2 = Point('2', 2.5)  # Point(x=2, y=2)
    assert p1 < p2        # True


A close equivalent traditional class would be much larger, would have to be
updated for any new attributes, and wouldn't support more advanced casting,
such as to types annotated using the ``typing`` module:

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
            return not self == other

        def __lt__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return (self.x, self.y) < (other.x, other.y)

        def __le__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return self == other or self < other

        def __gt__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return not self <= other

        def __ge__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return not self < other

        def __hash__(self):
            return hash((self.x, self.y))


Attributes can be declared optional either manually, by `using typing.Optional`
or by using the PEP 484 implicit optional of a default value of `None`.

.. code-block:: python

    from typing import Optional

    from typet import Object

    class Point(Object):
        x: Optional[int]
        y: int = None

    p1 = Point()   # Point(x=None, y=None)
    p2 = Point(5)  # Point(x=5, y=None)


Additionally, ``typet`` contains a suite of sliceable classes that will create
bounded, or validated, versions of those types that always assert their values
are within bounds; however, when an instance of a bounded type is instantiated,
the instance will be of the original type.

.. code-block:: python

    from typet import Bounded

    BoundedInt = Bounded[int, 10:20]

    x = BoundedInt(15)  # Okay
    type(x)             # <class 'int'>
    BoundedInt(5)       # Raises ValueError


To showcase the power of these classes, they can be combined these to create a
class that checks bounds, contains an optional attribute and defines common
methods automatically.

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


This class can be used intuitively:

.. code-block:: python

    Person('Jim', 'Coder', 23)            # Okay; hobby will be None
    Person('Jim', 'Coder', 230)           # Raises TypeError
    Person('Jim', 'Coder', 23, 'Python')  # Okay; sets hobby
    Person(name='Jim',                    # Keyword arguments are okay.
           surname='Coder',
           age=23)
    Person('Jim',                         # As is mixing and matching
           'Coder',                       # positional and keyword arguments.
           hobby='Python',
           age=23)


By using type aliases on validation types, the intent of the attribute is
clear, while giving the advantages of removing boiler plate code, enforcing
bounds, and declaring types for `mypy`.


Python 2.7 to 3.5
-----------------

``typet`` supports class type comments for annotations.

.. code-block:: python

    from typet import Object

    class Point(Object):
        x = None  # type: int
        y = None  # type: int

    p1 = Point(0, 0)      # Point(x=0, y=0)
    p2 = Point('2', 2.5)  # Point(x=2, y=2)
    assert p1 < p2        # True

Note that, because Python prior to 3.6 cannot annotate an attribute without
defining it, by convention, this will not imply a type of `Optional[int]`. If
the type is `Optional[int]`, it must be specified explicitly in the type
comment.

.. _typingplus: https://github.com/contains-io/typingplus/issues/1

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
