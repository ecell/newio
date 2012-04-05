#!/usr/bin/env python
# coding: utf-8
"""vizlog2world.py --- converts visualLog.h5 to world file.
"""
import sys, os

from h5py import File

from ecell4.lattice import LatticeSpace, LatticedParticle
from ecell4.world import World

class LatticeWorld(World):
    SPACE_REGISTRY = (('LatticeSpace', LatticeSpace),)

def main(args=sys.argv[1:]):
    
    if len(args)<2:
        sys.stderr.write('usage: vizlog2world.py visual_log_file output_file\n')
        raise SystemExit

    infile = File(args[0])
    out_name = os.path.splitext(os.path.split(args[1])[-1])[0]
    out_lw = LatticeWorld(name=str(out_name))
    data_group = infile['data']
    # print data_group, list(data_group)
    n_groups = len(data_group)
    print 'found %d groups.' %(n_groups)
    for i, (k, v) in enumerate(data_group.items()):
        print 'pricessing dataset %s (%d/%d)...' %(k, i, n_groups)
        particle_info = v['particles']
        ls = LatticeSpace(str(k))
        print 'converting particles...'
        ls.particles = [
            LatticedParticle(int(pid), int(sid), int(lid))
            for pid, sid, lid in particle_info]
        out_lw.spaces[str(k)] = ls
    out_lw.save(args[1])
        



if __name__=='__main__':
    main(args=['visualLog.h5', 'converted.hdf5'])
