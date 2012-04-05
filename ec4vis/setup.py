# coding: utf-8
# Copyright (c) 2010, 2011 Accense Technology, Inc. All rights reserved.

import glob, sys
from distutils.core import setup
try:
    from setuptools import setup
except ImportError:
    pass


version = '0.0.1'

args = sys.argv[1:]
if 'upload' in args or 'register' in args:
    sys.stderr.write("'upload' and 'register' are not allowed in this setup.py.\n")
    raise SystemExit
else:
    filtered_args = [a for a in args if a not in ['upload', 'register']]
    setup(
        script_args=filtered_args,
        name="ec4vis",
        version=version,
        description=("E-Cell4 data visualizer."),
        classifiers=["Development Status :: 4 - Beta",
                     "Intended Audience :: Developers",
                     # "License :: OSI Approved :: ",
                     "Programming Language :: Python",
                     "Topic :: Software Development :: Libraries :: Python Modules"],
        # author="Yasushi Masuda, Accense Technology, Inc.",
        # author_email="ymasuda at accense.com or whosaysni at gmail.com",
        url="http://e-cell.org/",
        # license="",
        zip_safe=True,
        packages=["ec4vis",
                  "ec4vis.plugins"],
        test_suite = 'tests.suite'
        )
