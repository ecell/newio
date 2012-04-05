# coding: utf-8
"""Particle class implementation.
"""
from collections import OrderedDict

from numpy import array, ndarray, zeros

from ecell4.space import Space
from ecell4.utils import *


class Particle(object):
    """Abstract particle definition.

    Attributes:
    id -- particle identifier
    species_id -- species identifier
    """
    def __init__(self, particle_id, species_id, position):
        self.id = particle_id
        self.species_id = species_id
        self.position = position

    def __repr__(self):
        return "<%s id='%s'>" %(self.__class__.__name__, self.id)


class CoordinatedParticle(Particle):
    """Represents a particle with coordinates.

    >>> pos = zeros((3,), dtype='float64')
    >>> pos[:] = [1.0, 2.0, 3.0]
    >>> p = CoordinatedParticle(0, 0, pos)
    >>> p
    <CoordinatedParticle id='0'>
    >>> p.id, p.species_id, p.position
    (0, 0, array([ 1.,  2.,  3.]))
    >>> p.x, p.y, p.z
    (1.0, 2.0, 3.0)
    >>> p.x, p.y, p.z = 4.0, 5, 6.0
    >>> p.position
    array([ 4.,  5.,  6.])
    
    """
    def __init__(self, particle_id, species_id, position):
        position = array(position) # TBD: need validation
        super(CoordinatedParticle, self).__init__(particle_id, species_id, position)
        
    
    # Just a hack.
    x, y, z = [
        property(lambda self, i=i: self.position[i],
                 lambda self, value, i=i: self.position.__setitem__(i, value))
        for i in range(3)]


class ParticleSpace(Space):
    """Represents a simple E-Cell4 particle space.

    # setup
    >>> import os, tempfile
    >>> tfname = tempfile.mktemp()

    # frob a ParticleSpace
    >>> s1 = ParticleSpace()
    >>> s1.name, s1.particles
    (None, [])
    >>> s2 = ParticleSpace('bar')
    >>> s2.name
    'bar'
    >>> s2.particles = [CoordinatedParticle(i, 0, (i, i*2, i*3)) for i in range(100)]
    >>> s2.particles, s2.particles[4].position
    ([<CoordinatedParticle id='0'>, <CoordinatedParticle id='1'>, ...], array([ 4,  8, 12]))
    >>>

    # save and load
    >>> s2.save(tfname)
    <HDF5 file "..." (mode r+)>

    >>> s3 = ParticleSpace.Load(tfname)
    >>> s3.particles, s2.particles[4].position
    ([<CoordinatedParticle id='0'>, <CoordinatedParticle id='1'>, ...], array([ 4,  8, 12]))
    
    # teardown
    >>> if os.path.exists(tfname): os.remove(tfname)
    
    
    """

    def __init__(self, name=None):
        """Initializer.

        Attributes:
        name: Name of the model. (inherited from Component).
        spaces: collection of space object
        
        """
        super(ParticleSpace, self).__init__(name) # implies self.name
        self.particles = []

    # ParticleSpace persistency support
    # 
    # Space's from_file(), load(), save() handles
    # "space file" format. The space file is a HDF5 data group.
    # whose layout can be described as below:
    #
    # <data root>--- application='ecell4', format='particlespace',
    #   |            version=(version number of 3 integers)
    #   |
    #   +---<metadata>--- name=(name string),
    #   |                 (and any model metadata (not defined yet))
    #   |
    #   +---<particles>--- n_particles=(integer)
    #         |            
    #         +---<id>
    #         |     (integer dataset of n_particles)
    #         +---<species_id>
    #         |     (integer dataset of n_particles)
    #         +---<position> 
    #               (float64 dataset of 3*n_particles)
    # 
    # Base cls.Load(), load(), save() are defined in Component.

    def _particles_schema(self, n_particles):
        """Internal utility to build particle schema"""
        return (('id', (n_particles,), 'int32'),
                ('species_id', (n_particles,), 'int32'),
                ('position', (n_particles, 3), 'float64'))

    def load(self, hdf5_or_filename, strict_version=True):
        """Load data from a file (into exisiting instance).

        This method ALWAYS OVERWRITE instance attribute with loaded file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        data_root = super(ParticleSpace, self).load(hdf5_or_filename, strict_version=True)
        # all green here, ready to update.
        # XXX TBD: This can be generalized to achieve abstract
        # particle-based space implementation...
        n_particles, species_id, position = 0, [], []
        particle_group = data_root.get('particles', None)
        dataset_values = []
        if particle_group:
            n_particles = particle_group.attrs.get('n_particles', 0)
            for name, shape, dtype in self._particles_schema(n_particles):
                dataset = particle_group.get(name, None)
                values = None
                if not dataset is None:
                    values = dataset.value
                if values is None:
                    values = zeros(shape, dtype)
                dataset_values.append(values)
        self.particles = [
            CoordinatedParticle(pid, sid, pos)
            for pid, sid, pos in zip(*dataset_values)]
        return data_root
            
    def save(self, hdf5_or_filename, strict_version=True):
        """Save data into a file.

        This method ALWAYS OVERWRITE data in exisisting file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        data_root = super(ParticleSpace, self).save(hdf5_or_filename, strict_version=True)
        # all green here, ready to serialize.
        n_particles = len(self.particles)
        particle_group = data_root.get('particles', None)
        if particle_group:
            del data_root['particles']
        particle_group = data_root.create_group('particles')
        particle_group.attrs['n_particles'] = n_particles
        # prepare generators
        array_dict = dict(
            id=array([p.id for p in self.particles]),
            species_id=array([p.species_id for p in self.particles]),
            position=array([p.position for p in self.particles]),)
        # create particles dataset
        for name, shape, dtype in self._particles_schema(n_particles):
            ### Important ###
            # existing dataset should be deleted first, because
            # length of the dataset may change dynamically in
            # a simulation.
            if name in particle_group.keys():
                del particle_group[name]
            dataset = particle_group.create_dataset(name, shape, dtype)
            # fill with values
            # TBD: array of length 0 may brake.
            dataset[...] = array_dict[name]
        return data_root
    
                                     
if __name__=='__main__':
    from doctest import testmod, ELLIPSIS
    testmod(optionflags=ELLIPSIS)
