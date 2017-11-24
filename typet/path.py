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
