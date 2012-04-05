import h5py

class Paticle(object):
    def __init__(self, id, species_id, position, radius):
        self.id         = id
        self.species_id = species_id
        self.x          = position[0]
        self.y          = position[1]
        self.z          = position[2]
        self.radius     = radius

class ParticleSpace(Space):
    def __init__(self):
        self.particles = []
    def add_particle(particle):
        self.particles.append(particle)

class Lattice(object):
    def __init__(self, id, species_id, compartment_id, radius):
        self.id             = id
        self.lattice_id     = lattice_id
        self.species_id     = species_id
        self.compartment_id = compartment_id
        self.radius         = radius

class LatticeCompartment(object):
    def __init__(self, id, lengths):
        self.id = id
        self.x  = lengths[0]
        self.y  = lengths[1]
        self.z  = lengths[2]

class LatticeSpace(Space):
    def __init__(self):
        self.lattces = []
    def add_lattice(lattice):
        self.lattces.append(lattice)

class Space(object):
    def __init__(self, logger):
        self.logger = SpaceLogger()

class SpaceLogger(object):
    def __init__(self, space):
        self.space = space

    def write_space(self, hdf5):
        handle = h5py.File(hdf5)
        handle.write(self.space)

    def read_space(self, hdf5):
        handle = h5py.File(hdf5)
        # todo: detect Space type(eGFRD or Spatiocyte) and create (Particle,Lattice)Space

