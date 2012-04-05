# coding: utf-8
"""Lattice class implementation.
"""
from collections import OrderedDict

from numpy import array, ndarray, zeros

from ecell4.space import Space
from ecell4.particle import Particle
from ecell4.utils import *


class LatticedParticle(Particle):
    """Represents a particle with lattice id.

    >>> p = LatticedParticle(0, 0, 42)
    >>> p
    <LatticedParticle id='0'>
    >>> p.id, p.species_id, p.position
    (0, 0, array(42))
    >>> p.lattice_id
    array(42)
    >>> p.lattice_id = 4242
    >>> p.lattice_id
    array(4242)
    
    """
    def __init__(self, particle_id, species_id, position):
        position = array(position) # TBD: need validation
        super(LatticedParticle, self).__init__(particle_id, species_id, position)
    lattice_id = property(lambda self: self.position,
                          lambda self, value: setattr(self, 'position', array(value)))
    

class LatticeSpace(Space):
    """Represents a simple E-Cell4 lattice space.

    # setup
    >>> import os, tempfile
    >>> tfname = tempfile.mktemp()

    # frob a LatticeSpace
    >>> s1 = LatticeSpace()
    >>> s1.name, s1.particles
    (None, [])
    >>> s2 = LatticeSpace('bar')
    >>> s2.name, s2.particles
    ('bar', [])
    >>> s2.particles = [LatticedParticle(i, 0, i**2) for i in range(100)]
    >>> s2.particles, s2.particles[4].lattice_id
    ([<LatticedParticle id='0'>, <LatticedParticle id='1'>, ...], array(16))
    >>>

    # save and load
    >>> s2.save(tfname)
    <HDF5 file "..." (mode r+)>

    >>> s3 = LatticeSpace.Load(tfname)
    >>> s3.particles, s2.particles[4].lattice_id
    ([<LatticedParticle id='0'>, <LatticedParticle id='1'>, ...], array(16))
    
    # teardown
    >>> if os.path.exists(tfname): os.remove(tfname)
    
    """

    def __init__(self, name=None):
        """Initializer.

        Attributes:
        name: Name of the model. (inherited from Component).
        spaces: collection of space object
        
        """
        super(LatticeSpace, self).__init__(name) # implies self.name
        self.particles = []

    # LatticeSpace persistency support
    # 
    # LatticeSpace's from_file(), load(), save() handles
    # "space file" format. The space file is a HDF5 data group.
    # whose layout can be described as below:
    #
    # <data root>--- application='ecell4', format='latticespace',
    #   |            version=(version number of 3 integers)
    #   |
    #   +---<metadata>--- name=(name string),
    #   |                 (and any model metadata (not defined yet))
    #   |
    #   |   # this could be unnecessary information, because it is
    #   |   # rather somewhat like model information.
    #   +---<lattice>--- lengths=(3*float64), voxel_radius=(float64),
    #   |                normalized_voxel_radius=(float64)
    #   |
    #   +---<particles>--- n_particles=(integer)
    #         |
    #         +---<id>
    #         |     (integer dataset of n_particles)
    #         +---<species_id>
    #         |     (integer dataset of n_particles)
    #         +---<lattice_id> 
    #               (integer dataset of n_particles)
    # 
    # Base cls.Load(), load(), save() are defined in Component.

    def _particles_schema(self, n_particles):
        """Internal utility to build particle schema"""
        return (('id', (n_particles,), 'int32'),
                ('species_id', (n_particles,), 'int32'),
                ('position', (n_particles,), 'int32'),)

    """DRAFT"""
    def load(self, hdf5_or_filename, strict_version=True):
        """Load data from a file (into exisiting instance).

        This method ALWAYS OVERWRITE instance attribute with loaded file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        data_root = super(LatticeSpace, self).load(hdf5_or_filename, strict_version=True)
        # all green here, ready to update.
        # XXX TBD: Almost similar with particlespace:
        #   This can be generalized to realize abstract
        #   particle-based space implementation...
        n_particles, species_id, position = 0, [], []
        particle_group = data_root.get('particles', None)
        dataset_values = []
        if particle_group:
            n_particles = particle_group.attrs.get('n_particles', 0)
            for name, shape, dtype in self._particles_schema(n_particles):
                dataset = particle_group.get(name, None)
                values = None
                if dataset is not None:
                     values = dataset.value
                if values is None:
                    values = zeros(shape, dtype)
                dataset_values.append(values)
        self.particles = [
            LatticedParticle(pid, sid, pos)
            for (pid, sid, pos) in zip(*dataset_values)]
        return data_root

    """DRAFT"""
    def save(self, hdf5_or_filename, strict_version=True):
        """Save data into a file.

        This method ALWAYS OVERWRITE data in exisisting file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        data_root = super(LatticeSpace, self).save(hdf5_or_filename, strict_version=True)
        # all green here, ready to serialize.
        particle_group = data_root.get('particles', None)
        n_particles = len(self.particles)
        if particle_group is None:
            particle_group = data_root.create_group('particles')
            particle_group.attrs['n_particles'] = n_particles
        dataset_dict = {}
        # prepare generators
        iter_dict = dict(
            id=(p.id for p in self.particles),
            species_id=(p.species_id for p in self.particles),
            position=(p.position for p in self.particles),)
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
            d = list(iter_dict[name])
            # avoid assignment of slice with a sequence of length 0, which may brake.
            if d:
                dataset[...] = d
            dataset_dict[name] = dataset
        return data_root


if __name__=='__main__':
    from doctest import testmod, ELLIPSIS
    testmod(optionflags=ELLIPSIS)
