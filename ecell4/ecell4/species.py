# coding: utf-8
"""Species class implementation
"""

from ecell4.base import Component
from ecell4.utils import *


class Species(Component):
    """Represents a species in E-Cell4 simulation model.

    Attributes:

    - name: name of the species.
    - diffusion: diffusion coefficient.
    - radius: interaction radius.
    - drift: drift velocity
    
    """

    def __init__(self, name, diffusion, radius, drift):
        """Initializer.
        """
        super(Species, self).__init__(self, name)
        self.diffusion = diffusion
        self.radius = radius
        self.drift = drift

    # convenient properties
    r = property(lambda s: s.radius, lambda s, v: setattr(s, 'radius', v))
    D = property(lambda s: s.diffusion, lambda s, v: setattr(s, 'diffusion', v))
    v = property(lambda s: s.drift, lambda s, v: setattr(s, 'drift', v))

    def save(self, hf, sv=True):
        saved = super(Species, self).save(hf, sv)
        saved.attrs['r'] = self.r
        saved.attrs['D'] = self.D
        saved.attrs['v'] = self.v
        return saved

    def load(self, hf, sv=True):
        loaded = super(Species, self).load(hf, sv)
        self.r = saved.attrs['r']
        self.D = saved.attrs['D']
        self.v = saved.attrs['v']
        return loaded


if __name__=='__main__':
    from doctest import testmod, ELLIPSIS
    testmod(optionflags=ELLIPSIS)
