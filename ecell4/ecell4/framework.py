# coding: utf-8
"""Simulator class implementation.
"""
from collections import OrderedDict

from ecell4.base import Component
from ecell4.utils import *


class Framework(Component):
    """Represents an E-cell4 framework.

    # setup
    >>> import os, tempfile
    >>> tfname = tempfile.mktemp()

    >>> f1 = Framework()
    >>> f1.name, f1.simulators
    (None, OrderedDict())
    >>> f2 = Framework('myfw')
    >>> f2.save(tfname)
    <HDF5 file "..." (mode r+)>
    
    # teardown
    >>> if os.path.exists(tfname): os.remove(tfname) # teardown
    
    """
    # (Persistency) version of this framework.
    VERSION = (0, 0, 1)
    # Versions of persistency this class supports.
    SUPPORTED_VERSIONS = [VERSION]
    # Simulator class registry
    SIMULATOR_REGISTRY = tuple() # should be a sequence of ('type', SimulatorClass)

    def __init__(self, name=None):
        """
        Initializer.
        
        Attributes:

        name: Name of the framework.
        simulators: (Ordered) dictionary of simulators in the framework.
        
        """
        super(Framework, self).__init__(name) # implies self.name
        self.simulators = OrderedDict()

    # Experimental: Framework persistency support
    # 
    # Framework's from_file(), load(), save() handles experimental
    # "framework file" format. The framework file is a HDF5 file,
    # whose layout can be described as below:
    #
    # <data root>--- application='ecell4', format='framework',
    #   |            version=(version number of 3 integers)
    #   |
    #   +---<metadata>--- name=(name string),
    #   |                 (and any framework metadata (not defined yet))
    #   |
    #   +---<simulators>
    #         |
    #         +---<"simulator1"> (named simulator), type='foosimulator'
    #         +---<"simulator2"> (named simulator), type='barsimulator'
    #         +---... (sequence of simulator data in the framework,
    #                  those are equivalent with Simulator's HDF5)
    #
    # Base cls.Load(), load(), save() are defined in Component.
    
    def load(self, hdf5_or_filename, strict_version=True):
        """Load data from a file (into exisiting instance).

        This method ALWAYS OVERWRITE instance attributes with loaded file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        data_root = super(Framework, self).load(hdf5_or_filename, strict_version=True)
        # all green here, ready to update.
        for i, simulator_data in enumerate(data_root.get('simulators', ())):
            simulator = load_component(
                simulator_data, self.SIMULATOR_REGISTRY, strict_version)
            self.simulators[simulator_data.name] = simulator
        return data_root

    def save(self, hdf5_or_filename, strict_version=True):
        """Save data into a file.

        This method ALWAYS OVERWRITE data in exisisting file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        data_root = super(Framework, self).save(hdf5_or_filename, strict_version=True)
        # all green here, ready to serialize.
        simulators_group = data_root.get('simulators', None)
        for name, simulator in self.simulators.items():
            # check if a named group already exists.
            save_named_component(simulators_group, name, simulator,
                                 self.SIMULATOR_REGISTRY, strict_version)
        return data_root
            
            

if __name__=='__main__':
    from doctest import testmod, ELLIPSIS
    testmod(optionflags=ELLIPSIS)
