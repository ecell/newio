# coding: utf-8
"""Simulator class implementation.
"""

from ecell4.logger import logger
from ecell4.base import Component
from ecell4.utils import *


class Simulator(Component):
    """Represents an E-cell4 simulator.

    Attributes:
    - model: Model parameters (network rules, species tables, etc).
    - state: Internal state of the simulator (random generators, counters, etc).
    - world: Mutatic status of simulated world (position of particles, etc).
    - logger: logging.Logger instance for event logging.

    # setup
    >>> import os, tempfile
    >>> tfname = tempfile.mktemp()

    # frobnicate simulator around.
    >>> s1 = Simulator()
    >>> s1.name, s1.model, s1.state, s1.world
    (None, None, None, None)
    >>> s2 = Simulator('foo')
    >>> s2.name, s2.model, s2.state, s2.world
    ('foo', None, None, None)

    # save goes.
    >>> s2.save(tfname)
    <HDF5 file "..." (mode r+)>

    # ... but reload fails bacause it lacks model/world.
    >>> s3 = Simulator.Load(tfname)
    Traceback (most recent call last):
    ...
    FileError: Could not find model group.

    # provide model/world and save.
    >>> from ecell4.model import Model
    >>> from ecell4.state import State
    >>> from ecell4.world import World
    >>> s2.model = Model('baz')
    >>> s2.state = State('qux')
    >>> s2.world = World('bar')
    >>> s2.name, s2.model, s2.state, s2.world
    ('foo', <Model 'baz'>, <State 'qux'>, <World 'bar'>)
    >>> Simulator.MODEL_REGISTRY = (('bazmodel', Model),)   # HACK
    >>> Simulator.STATE_REGISTRY = (('quxstate', State),)   # HACK
    >>> Simulator.WORLD_REGISTRY = (('barworld', World),)   # HACK
    >>> s2.save(tfname)
    <HDF5 file "..." (mode r+)>

    >>> s3 = Simulator.Load(tfname)
    >>> s3.name, s3.model, s3.state, s3.world
    ('foo', <Model 'baz'>, <State 'qux'>, <World 'bar'>)

    # teardown
    >>> if os.path.exists(tfname): os.remove(tfname)
    
    """
    # (Persistency) version of this simulator.
    VERSION = (0, 0, 1)
    # Versions of persistency this class supports.
    SUPPORTED_VERSIONS = [VERSION]
    # Model class registry
    MODEL_REGISTRY = tuple() # should be a sequence of ('type', ModelClass)
    # State class registry
    STATE_REGISTRY = tuple() # should be a sequence of ('type', StateClass)
    # World class registry
    WORLD_REGISTRY = tuple() # should be a sequence of ('type', WorldClass)

    def __init__(self, name=None, model=None, state=None, world=None, logger=logger):
        """Initializer.
        """
        super(Simulator, self).__init__(name) # implies self.name
        self.model = model
        self.state = state
        self.world = world
        self.logger = logger
        logger.debug('%s:: Instance initialized.' %(self.__class__.__name__))

    # convenient properties
    m = property(lambda self: self.model, lambda self, value: setattr(self, 'model', value))
    s = property(lambda self: self.state, lambda self, value: setattr(self, 'state', value))
    w = property(lambda self: self.world, lambda self, value: setattr(self, 'world', value))

    def setup(self):
        """Setup simulator. Subclasses should override this.
        """
        return NotImplemented

    def teardown(self):
        """Teardown simulator. Subclasses should override this.
        """
        return NotImplemented

    def step(self):
        """Do step culculation.
        """
        return NotImplemented

    def reset(self):
        """Resets any internal states.
        """
        return NotImplemented

    # Experimental: Simulator persistency support
    # 
    # Simulator's from_file(), load(), save() handles
    # "simulator file" format. The simulator file is a HDF5 file,
    # whose layout can be described as below:
    #
    # <data root>--- application='ecell4', format='simulator',
    #   |            version=(version number of 3 integers)
    #   |
    #   +---<metadata>--- name=(name string),
    #   |                 (and any simulator metadata (not defined yet))
    #   |
    #   +---<model>--- type=(modeltype string),
    #   |
    #   +---<state>--- type=(stateype string)
    #   |
    #   +---<world>--- type=(worldtype string)
    #   |
    #   |   XXX Another design of model structure XXX
    #   +---<model>--- type=(modeltype string),
    #   |     |
    #   |     +---<__fixture__> (collection of initial model parameters)
    #   |     |
    #   |     +---<snapshots> (TBD: discussion required)
    #   |           |
    #   |           +---<"name1"> (named model snapshot)
    #   |           +---<"name2"> (named model snapshot)
    #   |           +---<"name3"> (named model snapshot)
    #   |           ...
    #   |
    #   |   XXX Another design of world structure XXX
    #   +---<world>
    #   |     |
    #   |     +---<__fixture__> (collection of initial world datasets)
    #   |     |
    #   |     +---<snapshots> (TBD: discussion required for layouts)
    #   |           |
    #   |           +---<"name1"> (named world snapshot)
    #   |           +---<"name2"> (named world snapshot)
    #   |           +---<"name3"> (named world snapshot)
    #   |           ...
    #   |
    #   +---<models/worlds>
    #             (future version may support this)
    # 
    # Base cls.Load(), load(), save() are defined in Component.

    def load_sub_component(self, hdf5_or_filename, name, registry, strict_version=True):
        """Load sub-component from named group and registry.
        """
        data_root = find_hdf5(hdf5_or_filename, new=False)
        data_group = data_root.get(name, None)
        if data_group is None:
            raise FileError('Could not find %s group.' %(name))
        else:
            loaded = load_component(data_group, registry, strict_version)
            setattr(self, name, loaded)
        return loaded
            
    def save_sub_component(self, hdf5_or_filename, name, registry, strict_version=True):
        """Save sub-component from named group and registry.
        """
        data_root = find_hdf5(hdf5_or_filename, new=False)
        component = getattr(self, name, None)
        if component:
            saved = save_named_component(
                data_root, name, component, registry, strict_version)
            return saved
            
    # These methods are redundant to support fine-tuned loading of model/state/world.
    def load_model(self, hdf5_or_filename, strict_version=True):
        """Loads model from an existing simulator HDF5 file."""
        return self.load_sub_component(
            hdf5_or_filename, 'model', self.MODEL_REGISTRY, strict_version)

    def load_state(self, hdf5_or_filename, strict_version=True):
        """Loads state from an existing simulator HDF5 file."""
        return self.load_sub_component(
            hdf5_or_filename, 'state', self.STATE_REGISTRY, strict_version)

    def load_world(self, hdf5_or_filename, strict_version=True):
        """Loads model from an existing simulator HDF5 file."""
        return self.load_sub_component(
            hdf5_or_filename, 'world', self.WORLD_REGISTRY, strict_version)

    # These methods are also redundant to support fine-tuned saving of model/state/world.
    def save_model(self, hdf5_or_filename, strict_version=True):
        """Saves the model into a simulator HDF5 file."""
        return self.save_sub_component(
            hdf5_or_filename, 'model', self.MODEL_REGISTRY, strict_version)

    def save_state(self, hdf5_or_filename, strict_version=True):
        """Saves the state into a simulator HDF5 file."""
        return self.save_sub_component(
            hdf5_or_filename, 'state', self.STATE_REGISTRY, strict_version)

    def save_world(self, hdf5_or_filename, strict_version=True):
        """Saves the world into a simulator HDF5 file."""
        return self.save_sub_component(
            hdf5_or_filename, 'world', self.WORLD_REGISTRY, strict_version)
     
    def load(self, hdf5_or_filename, strict_version=True):
        """Load data from a file (into exisiting instance).

        This method ALWAYS OVERWRITE instance attribute with loaded file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        data_root = super(Simulator, self).load(hdf5_or_filename, strict_version=True)
        # all green here, ready to update.
        self.load_model(data_root, strict_version)
        self.load_state(data_root, strict_version)
        self.load_world(data_root, strict_version)
        logger.debug('%s:: loaded from %s.' %(self.__class__.__name__, hdf5_or_filename))
        return data_root

    def save(self, hdf5_or_filename, strict_version=True):
        """Save data into a file.

        This method ALWAYS OVERWRITE data in exisisting file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        data_root = super(Simulator, self).save(hdf5_or_filename, strict_version=True)
        # all green here, ready to serialize.
        self.save_model(data_root, strict_version)
        self.save_state(data_root, strict_version)
        self.save_world(data_root, strict_version)
        logger.debug('%s:: saved to %s.' %(self.__class__.__name__, hdf5_or_filename))
        return data_root


if __name__=='__main__':
    from doctest import testmod, ELLIPSIS
    testmod(optionflags=ELLIPSIS)
