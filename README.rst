typet
=====

|PyPI| |Python Versions| |Build Status| |Coverage Status| |Code Quality|

*Types that make validating types in Python easy.*

typet works best with Python 3.6 or later. Prior to 3.6, validation types are
supported, but the object types cannot be supported until ``typingplus``
supports class type comments.


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


.. |Build Status| image:: https://travis-ci.org/contains-io/typet.svg?branch=master
   :target: https://travis-ci.org/contains-io/typet
.. |Coverage Status| image:: https://coveralls.io/repos/github/contains-io/typet/badge.svg?branch=master
   :target: https://coveralls.io/github/contains-io/typet?branch=master
.. |PyPI| image:: https://img.shields.io/pypi/v/typet.svg
   :target: https://pypi.python.org/pypi/typet/
.. |Python Versions| image:: https://img.shields.io/pypi/pyversions/typet.svg
   :target: https://pypi.python.org/pypi/typet/
.. |Code Quality| .. image:: https://api.codacy.com/project/badge/Grade/dae19ee1767b492e8bdf5edb16409f65
   :target: https://www.codacy.com/app/contains-io/typet?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=contains-io/typet&amp;utm_campaign=Badge_Grade
