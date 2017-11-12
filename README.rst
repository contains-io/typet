typet
=====

|PyPI| |Python Versions| |Build Status| |Coverage Status| |Code Quality|

*Types that make validating types in Python easy.*

typet works best with Python 3.6 or later. Prior to 3.6, validation types are
supported, but the object types cannot be supported until typingplus_ supports
class type comments.


Installation
------------

Install it using pip:

::

    pip install typet


Features
--------

- Validation types that can be used while casting to validate an object's
  content.


Basic Usage
-----------

One of the cooler features of ``typet`` is the ability to create complex
objects with very little code. The following code creates an object that
generates properties from the annotated class attributes that will ensure that
only values of *int* or that can coerced into *int* can be set. It also
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

    class Point:

        def __init__(self, x, y):
            self.x = x
            self.y = y

        def __repr__(self):
            return 'Point(x={x}, y={y})'.format(x=self.x, y=self.y)

        def __setattr__(self, name, value):
            if name in ('x', 'y'):
                value = int(value)
            super().__setattr__(name, value)

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


Future Usage for Python 2.7 to 3.5
----------------------------------

In the future, ``typet`` will support class type comments for annotations.

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
