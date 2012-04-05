import h5py
from space import SpaceLogger

class World(object):
    def __init__(self, logger):
        self.model  = model
        self.logger = WorldLogger()
        self.space_for = {}

    def add_space(time, space):
        spece_for[time] = space

class WorldLogger(object):
    def __init__(self, world):
        self.world = world
    
    def write_world(self, hdf5):
        handle = h5py.File(hdf5)
        # todo: write fields in World on hdf5 
        
    def read_world(self, hdf5):
        handle = h5py.File(hdf5)
        # todo: create instance of World
        return world

