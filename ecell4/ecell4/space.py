# coding: utf-8
"""Space class implementation.
"""

from ecell4.base import Component
from ecell4.utils import *


class Space(Component):
    """Represents an E-Cell4 model.

    # setup
    >>> import os, tempfile
    >>> tfname = tempfile.mktemp()
    
    >>> s1 = Space()
    >>> s1.name
    >>> s1 = Space('bar')
    >>> s1.time = 100.125
    >>> s1.save(tfname)
    <HDF5 file "..." (mode r+)>
    >>> s2 = Space.Load(tfname)
    >>> s2.name, s2.time
    ('bar', 100.125)
    >>> s3 = Space('baz')
    >>> s3.name, s3.time
    ('baz', 0)
    >>> s3.load(tfname)
    <HDF5 file "..." (mode r+)>
    >>> s3.name, s3.time
    ('bar', 100.125)

    # teardown
    >>> if os.path.exists(tfname): os.remove(tfname) # teardown
    
    """
    # (Persistency) version of this framework.
    VERSION = (0, 0, 1)
    # Versions of persistency this class supports.
    SUPPORTED_VERSIONS = [VERSION]

    def __init__(self, name=None, time=0):
        """Initializer.

        Attributes:
        name: Name of the space. (inherited from Component).
        spaces: collection of space object
        
        """
        super(Space, self).__init__(name) # implies self.name
        self.time = time

    # Space persistency support
    # 
    # Space's from_file(), load(), save() handles
    # "space file" format. The space file is a HDF5 data group.
    # whose layout can be described as below:
    #
    # <data root>--- application='ecell4', format='space',
    #   |            version=(version number of 3 integers),
    #   |            time=(float64), ..
    #   |
    #   +---<metadata>--- name=(name string),
    #                     (and any space metadata (not defined yet))
    #
    # Base cls.Load(), load(), save() are defined in Component.

    def load(self, hdf5_or_filename, strict_version=True):
        """Load data from a file (into exisiting instance).

        This method ALWAYS OVERWRITE instance attribute with loaded file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        data_root = super(Space, self).load(hdf5_or_filename, strict_version=True)
        # all green here, ready to update.
        self.time = data_root.attrs.get('time', 0)
        return data_root

    def save(self, hdf5_or_filename, strict_version=True):
        """Save data into a file.

        This method ALWAYS OVERWRITE data in exisisting file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        data_root = super(Space, self).save(hdf5_or_filename, strict_version=True)
        # all green here, ready to serialize.
        data_root.attrs['time'] = self.time
        return data_root


if __name__=='__main__':
    from doctest import testmod, ELLIPSIS
    testmod(optionflags=ELLIPSIS)
