# coding: utf-8
"""State class implementation.
"""

from ecell4.base import Component
from ecell4.utils import *


class State(Component):
    """Represents an E-Cell4 state.

    # setup
    >>> import os, tempfile
    >>> tfname = tempfile.mktemp()

    # frobnicate state around.
    >>> m1 = State()
    >>> m1.name              # returns None
    >>> m2 = State('foo')
    >>> m2.name
    'foo'

    # save and load.
    >>> m2.save(tfname)
    <HDF5 file "..." (mode r+)>
    >>> m3 = State.Load(tfname)
    >>> m3.name
    'foo'
    
    # teardown
    >>> if os.path.exists(tfname): os.remove(tfname)
    
    """
    # (Persistency) version of this state.
    VERSION = (0, 0, 1)
    # Versions of persistency this class supports.
    SUPPORTED_VERSIONS = [VERSION]

    def __init__(self, name=None):
        """Initializer.

        Attributes:
        name: Name of the state. (inherited from Component).
        spaces: collection of space object
        
        """
        super(State, self).__init__(name) # implies self.name

    # State persistency support
    # 
    # State's from_file(), load(), save() handles
    # "state file" format. The state file is a HDF5 data group.
    # whose layout can be described as below:
    #
    # <data root>--- application='ecell4', format='state',
    #   |            version=(version number of 3 integers)
    #   |
    #   +---<metadata>--- name=(name string),
    #                     (and any state metadata (not defined yet))
    # 
    # Base cls.Load(), load(), save() are defined in Component.

    def load(self, hdf5_or_filename, strict_version=True):
        """Load data from a file (into exisiting instance).

        This method ALWAYS OVERWRITE instance attribute with loaded file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        data_root = super(State, self).load(hdf5_or_filename, strict_version=True)
        # all green here, ready to update.
        return data_root

    def save(self, hdf5_or_filename, strict_version=True):
        """Save data into a file.

        This method ALWAYS OVERWRITE data in exisisting file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        data_root = super(State, self).save(hdf5_or_filename, strict_version=True)
        # all green here, ready to serialize.
        return data_root
        


if __name__=='__main__':
    from doctest import testmod, ELLIPSIS
    testmod(optionflags=ELLIPSIS)
