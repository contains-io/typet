# -*- coding: utf-8 -*-
"""A module containing types representing file and directory states.

Classes:
    File: A type instance of Valid that validates that the value is a file.
    Dir: A type instance of Valid that validates that the value is a directory.
    Path: A type instance of Valid that expands a value to a path.
"""

from __future__ import unicode_literals

import os.path

from .validation import Valid

try:
    import pathlib
except ImportError:
    import pathlib2 as pathlib  # type: ignore


def _valid(name, type_, predicate):
    new_type = Valid[type_, predicate]
    setattr(
        new_type, "__class_repr__", "{}.{}".format(predicate.__module__, name)
    )
    return new_type


def is_dir(path):
    """Determine if a Path or string is a directory on the file system."""
    try:
        return path.expanduser().absolute().is_dir()
    except AttributeError:
        return os.path.isdir(os.path.abspath(os.path.expanduser(str(path))))


def is_file(path):
    """Determine if a Path or string is a file on the file system."""
    try:
        return path.expanduser().absolute().is_file()
    except AttributeError:
        return os.path.isfile(os.path.abspath(os.path.expanduser(str(path))))


def exists(path):
    """Determine if a Path or string is an existing path on the file system."""
    try:
        return path.expanduser().absolute().exists()
    except AttributeError:
        return os.path.exists(os.path.abspath(os.path.expanduser(str(path))))


Dir = _valid("Dir", pathlib.Path, is_dir)
File = _valid("File", pathlib.Path, is_file)
ExistingPath = _valid("ExistingPath", pathlib.Path, exists)
