# coding: utf-8
"""Reaction rule class implementation
"""

from ecell4.base import Component
from ecell4.utils import *


class ReactionRule(Component):
    """Represents a species in E-Cell4 simulation model.

    Attributes:

    - name: name of the reaction rule.
    - bound: name of bound species
    - unbound: (tuple of) name of unbound species
    - k: reaction coefficient
    - is_binding: True: binding reaction, False:unbindng reaction.
    
    """

    def __init__(self, name, bound, unbound, k, is_binding):
        """Initializer.
        """
        super(Species, self).__init__(self, name)
        self.bound = bound
        self.unbound = unbound
        self.k = k
        self.is_binding = is_binding

    def set_repulsive(self):
        self.k = 0

    def save(self, hf, sv=True):
        saved = super(Species, self).save(hf, sv)
        saved.attrs['bound'] = self.bound
        saved.attrs['unbound_a'] = self.unbound[0]
        saved.attrs['unbound_b'] = self.unbound[1]
        saved.attrs['k'] = self.k
        saved.attrs['is_binding'] = self.is_binding
        return saved

    def load(self, hf, sv=True):
        loaded = super(Species, self).load(hf, sv)
        self.bound = saved.attrs['bound']
        self.unbound_a = saved.attrs['unbound_a']
        self.unbound_b = saved.attrs['unbound_b']
        self.k = saved.attrs['k']
        self.is_binding = saved.attrs['is_binding']
        return loaded


if __name__=='__main__':
    from doctest import testmod, ELLIPSIS
    testmod(optionflags=ELLIPSIS)
