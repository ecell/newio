# coding: utf-8
"""Attic for code fragments.
"""
# Simulator registry is a dictionary which maps simulator name to
# actual simulator class.
_CLASS_REGISTRY = {}

#
# class MySimulator(Simulator):
#   ... <some fine tune with your Simulator class>...
#
# from simulator import register
# register(MySimulator, 'mysimulator')

def register(cls, klass, name=None):
    """Register klass into the class regstry.

    If name is omitted class's __name__ attribute is used.
    """
    if name is None:
        name = SimulatorClass.__name__
    _CLASS_REGISTRY[name] = SimulatorClass

def load_simulator(simulator_data, registry=_CLASS_REGISTRY, strict_version=True):
    """Load simulator instance of given class_name and data.

    >>> class Nonexistent(object):
    ...   attrs = dict(type='nonexistent')
    >>> load_simulator(, {})
    Traceback (most recent call last):
    ...
    ValueError: Could not find imulator class of nonexistent. Make sure you have register()ed it.
    >>> class DummySimulator(Simulator):
    ...   def load(self, data, strictv): self.name = data
    ...
    >>> load_simulator('dummy', 'foo', dict(dummy=DummySimulator), False)
    <DummySimulator 'foo'>
    
    """
    simulator_type = simulator_data.attrs.get('type', None)
    SimulatorClass = registry.get(simulator_class_name, None)
    if SimulatorClass is None:
        raise ValueError(
            'Could not find imulator class of %s. '
            'Make sure you have register()ed it.' %(simulator_class_name))
    return SimulatorClass.Load(simulator_data, strict_version)
    
    
# coding: utf-8
import copy, logging

from ecell4.logger import logger
from ecell4.storage import Simulator as SimulatorStorage


class Simulator(object):
    """Abstract base class for simulator.

    Attributes:

    - name: Name of the simulator.
    - model: Model parameters (network rules, species tables, etc).
    - state: Internal state of the simulator (random generators, counters, etc).
    - world: Mutatic status of simulated world (position of particles, etc).
    - logger: logging.Logger instance for event logging.
    - storage: Storage for the simulator.

    >>> sim = Simulator('foo')
    >>> sim
    <Simulator: "foo">
    >>> sim.name, sim.model, sim.state, sim.world
    ('foo', None, None, None)
    >>> sim.name, sim.model, sim.state, sim.world
    ('foo', None, None, None)
    >>> all((sim.model is sim.m, sim.state is sim.s, sim.world is sim.w,))
    True
    
    """

    def __init__(self, name=None, model=None, state=None, world=None,
                 logger=logger, storage=None):
        """Initializer.
        """
        self.name = name
        # save current state as fixture
        self.model = model
        self.state = state
        self.world = world
        self.logger = logger
        self.storage = storage

    def __repr__(self):
        return '<%s: "%s">' %(self.__class__.__name__, self.name)

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

    def save(self):
        """Save entire simulator state to storage. Subclass may extend this.
        """
        if self.storage is None:
            raise ValueError("storage hasn't set yet.")
        # 

    def restore(self):
        """
        """
        storage = 

    def resume(self):
        """
        """

class EGFRDSimulatorResumeState(object):
    """Represents a resuming state for EGFRDSimulator
    """
    
    VERSION = (0, 9, 0)
    PARTICLES_STATE_SCHEMA = [
        ('id', 'u8'),
        ('species_id', 'u8'),
        ('position', 'f8', (3, )),]
    SPECIES_ID_MAP_SCHEMA = [
        ('name', 'S32'),
        ('id', 'u8'),]

    def __init__(self, hdf5_file=None):
        self.step_counter = 0
        self.species_id_map = {}
        self.particles_state = []

        if hdf5_file:
            self.load_from_file(hdf5_file)

    def load(self, hdf5_file_path):
        """Load status from a hdf5 file.
        """
        import h5py
        try:
            hdf5_file = h5py.File(hdf5_file_path, 'r')
            version = tuple(hdf5_file.attrs['version'])
            if version>VERSION:
                raise Warning(u"File version exceeds EGFRDResumeState's one.")
            # load metadata/state sections
            metadata = hdf5_file['metadata']
            state = hdf5_file['state']
            # load species id map
            for name, id_ in state['species_id_map']:
                self.species_id_map[name] = id_
            # load step_counter
            self.step_counter = state.attrs['step_counter']
            # load particle state
            self.particles_state = [
                (id_, species_id, position)
                for id_, species_id, position in state]
        finally:
            hdf5_file.close()

    def save(self, hdf5_file_path):
        """Save status into a hdf5 file.
        """
        import h5py
        try:
            hdf5_file = h5py.File(hdf5_file_path, 'w')
            hdf5_file.attrs['version'] = self.VERSION
            metadata = hdf5_file.create_group('metadata')
            # save species id map
            sid_map = numpy.zeros(
                (len(self.species_id_map.keys()),),
                dtype=numpy.dtype(self.SPECIES_ID_MAP_SCHEMA))
            for idx, (name, id_) in enumerate(self.species_id_map.items()):
                sid_map['name'][idx] = name
                sid_map['id'][idx] = id_
            species_id_map = metadata.create_dataset('species_id_map', data=sid_map)
            # save particle state
            particles_state = numpy.zeros(
                (len(self.particles), ),
                dtype=numpy.dtype(self.PARTICLES_STATE_SCHEMA))
            for idx, (id_, species_id, position) in enumerate(self.particles_state):
                particles_state['id'][idx] = id_
                particles_state['species_id'] = species_id
                particles_state['position'] = position
            state_dataset = hdf5_file.create_dataset('state', data=particles_state)
            state_dataset.attrs['step_counter'] = self.step_counter
        finally:
            hdf5_file.close()


if __name__=='__main__':
    from doctest import testmod, ELLIPSIS
    testmod(optionflags=ELLIPSIS)

