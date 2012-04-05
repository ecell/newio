# coding: utf-8
"""Test suite, by Yasushi Masuda (ymasuda@accense.com)
"""


import doctest, imp, os, sys, unittest
sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

suite = unittest.TestSuite()

# #0 Doctest-based test suites

######
# TODO: Some doctests generates HDF5 files but no teardown is implemented yet.
######

module_paths = [
    # packages
    # modules
    ]

modules_dict = {}
for module_path in module_paths:
    bits = module_path.split('.')
    if len(bits)==1:
        path = None
        module_name = bits[0]
    elif len(bits)>1:
        prefix = '.'.join(bits[:-1])
        path = modules_dict[prefix].__path__
        module_name = bits[-1]
    loaded = imp.load_module(module_name, *imp.find_module(module_name, path))
    modules_dict[module_path] = loaded
    try:
        suite.addTests(doctest.DocTestSuite(loaded, optionflags=doctest.ELLIPSIS))
    except ValueError, e:
        # addTests fails if there's no test in the module, just omit it.
        pass
        
# TBD: edge tests.
