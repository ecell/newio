# coding: utf-8
"""World class implementation.
"""
from collections import OrderedDict
from datetime import datetime

from ecell4.base import Component
from ecell4.utils import *


class World(Component):
    """Represents an E-Cell4 world.

    # setup
    >>> import os, tempfile
    >>> tfname = tempfile.mktemp()

    # frobnicate world around.
    >>> w1 = World('foo')
    >>> w1.name, w1.spaces
    ('foo', OrderedDict())

    # save and load
    >>> w1.save(tfname)
    <HDF5 file "..." (mode r+)>
    >>> w1 = World.Load(tfname)

    # teardown
    >>> if os.path.exists(tfname): os.remove(tfname)
    
    """
    # (Persistency) version of this framework.
    VERSION = (0, 0, 1)
    # Versions of persistency this class supports.
    SUPPORTED_VERSIONS = [VERSION]
    SPACE_REGISTRY = tuple() # should be a sequence of ('type', SpaceClass)

    def __init__(self, name=None):
        """Initializer.

        Attributes:
        name: Name of the world. (inherited from Component).
        spaces: collection of space object
        
        """
        super(World, self).__init__(name) # implies self.name
        self.spaces = OrderedDict()

    # World persistency support
    # 
    # World's from_file(), load(), save() handles
    # "world file" format. The world file is a HDF5 data group.
    # whose layout can be described as below:
    #
    # <data root>--- application='ecell4', format='world',
    #   |            version=(version number of 3 integers)
    #   |
    #   +---<metadata>--- name=(name string),
    #   |                 (and any world metadata (not defined yet))
    #   |
    #   +---<spaces>--- type=(space type string),
    #         |
    #         +---<"name1"> (named space snapshot) time=1, ...
    #         +---<"name2"> (named space snapshot) time=2, ...
    #         +---<"name3"> (named space snapshot) time=3, ...
    #         ...
    # 
    # Base cls.Load(), load(), save() are defined in Component.

    def load(self, hdf5_or_filename, strict_version=True):
        """Load data from a file (into exisiting instance).

        This method ALWAYS OVERWRITE instance attribute with loaded file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        data_root = super(World, self).load(hdf5_or_filename, strict_version=True)
        # all green here, ready to update.
        # world
        spaces_group = data_root.get('spaces', None)
        if spaces_group is None:
            raise FileError('Could not find spaces group.')
        else:
            for name, space in spaces_group.items():
                self.spaces[name] = load_component(
                    space, self.SPACE_REGISTRY, strict_version)
        return data_root

    def save(self, hdf5_or_filename, strict_version=True):
        """Save data into a file.

        This method ALWAYS OVERWRITE data in exisisting file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        data_root = super(World, self).save(hdf5_or_filename, strict_version=True)
        # all green here, ready to serialize.
        spaces_group = data_root.get('spaces', None)
        timestamp = datetime.now().isoformat()
        if spaces_group is None:
            spaces_group = data_root.create_group('spaces')
        for name, space in self.spaces.items():
            saved = save_named_component(
                spaces_group, name, space,
                self.SPACE_REGISTRY, strict_version)
            saved.attrs['time'] = timestamp
        return data_root


if __name__=='__main__':
    from doctest import testmod, ELLIPSIS
    testmod(optionflags=ELLIPSIS)
