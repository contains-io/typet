#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Install typet."""

from __future__ import unicode_literals

from setuptools import setup
from setuptools import find_packages


setup(
    name="typet",
    use_scm_version=True,
    description="A library of types that simplify working with typed Python.",
    long_description=open("README.rst").read(),
    author="Melissa Nuño",
    author_email="dangle@contains.io",
    url="https://github.com/contains-io/typet",
    keywords=[
        "typing",
        "schema" "validation",
        "types",
        "annotation",
        "PEP 483",
        "PEP 484",
        "PEP 526",
    ],
    license="MIT",
    packages=find_packages(exclude=["tests", "docs"]),
    install_requires=["pathlib2", "typingplus >= 2.2.2, < 3"],
    setup_requires=["pytest-runner", "setuptools_scm"],
    tests_require=["pytest >= 3.2"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Intended Audience :: Developers",
        "Topic :: Software Development",
    ],
)
