#!/usr/env python

from weakref import ref
import math

import numpy

from _gfrd import (
    Event,
    EventScheduler,
    Particle,
    SphericalShell,
    SphericalShellContainer,
    CylindricalShell,
    CylindricalShellContainer,
    DomainIDGenerator,
    ShellIDGenerator,
    DomainID,
    ParticleContainer,
    CuboidalRegion,
    CylindricalSurface,
    PlanarSurface,
    _random_vector,
    Sphere,
    NetworkRulesWrapper,
    )

from gfrdbase import *
from single import *
from pair import *
from multi import *
from utils import *
from constants import *

import logging
import os

from bd import DEFAULT_DT_FACTOR

log = logging.getLogger('ecell')

if __debug__:
    PRECISION = 3
    FORMAT_DOUBLE = '%.' + str(PRECISION) + 'g'

def create_default_single(domain_id, pid_particle_pair, shell_id, rt, surface):
    if isinstance(surface, CuboidalRegion):
        return SphericalSingle(domain_id, pid_particle_pair,
                               shell_id, rt, surface)
    elif isinstance(surface, CylindricalSurface):
        return CylindricalSurfaceSingle(domain_id, pid_particle_pair, 
                                        shell_id, rt, surface)
    elif isinstance(surface, PlanarSurface):
        return PlanarSurfaceSingle(domain_id, pid_particle_pair, 
                                   shell_id, rt, surface)

def create_default_pair(domain_id, com, single1, single2, shell_id, 
                        r0, shell_size, rt, surface):
    if isinstance(surface, CuboidalRegion):
        return SphericalPair(domain_id, com, single1, single2,
                             shell_id, r0, shell_size, rt, surface)
    elif isinstance(surface, CylindricalSurface):
        return CylindricalSurfacePair(domain_id, com, single1, single2,
                                      shell_id, r0, shell_size, rt, surface)
    elif isinstance(surface, PlanarSurface):
        return PlanarSurfacePair(domain_id, com, single1, single2,
                                 shell_id, r0, shell_size, rt, surface)


class DomainEvent(Event):
    __slot__ = ['data']
    def __init__(self, time, domain):
        Event.__init__(self, time)
        self.data = domain

class Delegate(object):
    def __init__(self, obj, method, arg):
        self.ref = ref(obj)
        self.method = method
        self.arg = arg

    def __call__(self):
        return self.method(self.ref(), self.arg)


from ecell4.world import World
from ecell4.particle import ParticleSpace, CoordinatedParticle
class ParticleWorld(World):
    SPACE_REGISTRY = (('ParticleSpace', ParticleSpace),)


class EGFRDSimulator(ParticleSimulatorBase):
    """
    """
    def __init__(self, world, rng=myrandom.rng, network_rules=None, resume_state=None):
        """Create a new EGFRDSimulator.

        Arguments:
            - world
                a world object created with the function 
                gfrdbase.create_world.
            - rng
                a random number generator. By default myrandom.rng is 
                used, which uses Mersenne Twister from the GSL library.
                You can set the seed of it with the function 
                myrandom.seed.
            - network_rules
                you don't need to use this, for backward compatibility only.

        """
        if network_rules == None:
            network_rules = NetworkRulesWrapper(world.model.network_rules)
        ParticleSimulatorBase.__init__(self, world, rng, network_rules)

        self.domain_id_generator = DomainIDGenerator(0)
        self.shell_id_generator = ShellIDGenerator(0)

        self.MULTI_SHELL_FACTOR = 0.05
        self.SINGLE_SHELL_FACTOR = 1.1

        self.is_dirty = True
        self.scheduler = EventScheduler()

        self.user_max_shell_size = numpy.inf

        self.domains = {}

        self.reset()

    def save_space(self, hdf5_or_filename, space_name=None):
        """Retrive spacesnapshot of particle space from the simulator.
        """
        if space_name is None:
            # use timestamp if no space_name is given.
            import time
            space_name = str(time.time())
        else:
            space_name = str(space_name)
        pw = ParticleWorld('egfrd_snapshots')
        ps = ParticleSpace(str(space_name))
        # retrieve particles
        w = self.world
        ps.particles = []
        for species in w.species:
            ps.particles.extend(
                [CoordinatedParticle(id_.serial, species.id.serial,
                                     w.get_particle(id_)[1].position)
                 for id_ in w.get_particle_ids(species.id)])
        # save
        pw.spaces[space_name] = ps
        saved = pw.save(hdf5_or_filename)
        saved.close()
    
    def restore_space(self, hdf5_or_filename, space_name=None):
        """Restore saved particle space into the simulator.
        """
        pw = ParticleWorld.Load(hdf5_or_filename)
        if len(pw.spaces.keys())<1:
            # there should be at least one available saved space.
            raise ValueError('No saved space found.')
        if not space_name is None:
            # if space_name is specified find named space.
            ps = pw.spaces.get(space_name, None)
            if ps is None:
                raise ValueError('Could not find space named: %s' %(space_name))
        else:
            # ...otherwise, load latest space.
            ps = pw.spaces.items()[-1][1]
        # prepare maping from integer to speciesID 
        species_dict = dict((int(sp.id.serial), sp.id) for sp in self.get_species())
        for particle in ps.particles:
            self.world.new_particle(species_dict[particle.species_id], particle.position)

    def get_matrix_cell_size(self):
        return self.containers[0].cell_size

    def get_next_time(self):
        if self.scheduler.size == 0:
            return self.t

        return self.scheduler.top[1].time

    def set_user_max_shell_size(self, size):
        self.user_max_shell_size = size

    def get_user_max_shell_size(self):
        return self.user_max_shell_size

    def get_max_shell_size(self):
        return min(self.get_matrix_cell_size() * .5 / SAFETY,
                   self.user_max_shell_size)

    def reset(self):
        self.t = 0.0
        self.dt = 0.0
        self.step_counter = 0
        self.single_steps = {EventType.SINGLE_ESCAPE:0,
                             EventType.SINGLE_REACTION:0}
        self.interaction_steps = {EventType.IV_INTERACTION:0,
                                  EventType.IV_ESCAPE:0}
        self.pair_steps = {EventType.SINGLE_REACTION:0,
                           EventType.IV_REACTION:0,
                           EventType.IV_ESCAPE:0,
                           EventType.COM_ESCAPE:0}
        self.multi_steps = {EventType.MULTI_ESCAPE:0,
                            EventType.MULTI_UNIMOLECULAR_REACTION:0,
                            EventType.MULTI_BIMOLECULAR_REACTION:0, 3:0}
        self.zero_steps = 0
        self.rejected_moves = 0
        self.reaction_events = 0
        self.last_event = None
        self.last_reaction = None

        self.is_dirty = True

    def initialize(self):
        ParticleSimulatorBase.initialize(self)

        self.scheduler.clear()
        self.containers = [SphericalShellContainer(self.world.world_size, 
                                                   self.world.matrix_size),
                           CylindricalShellContainer(self.world.world_size, 
                                                     self.world.matrix_size)]
        self.domains = {}

        singles = []

        # Fix order of adding particles (always, or at least in debug mode).
        pid_particle_pairs = list(self.world)
        pid_particle_pairs.sort()

        for pid_particle_pair in pid_particle_pairs:
            single = self.create_single(pid_particle_pair)
            if __debug__:
                log.debug('%s as single %s' %
                          (pid_particle_pair[0], single.domain_id))
            singles.append(single)
        assert len(singles) == self.world.num_particles
        for single in singles:
            self.add_single_event(single)

        self.is_dirty = False

    def stop(self, t):
        """Synchronize all particles at time t.

        With eGFRD, particle positions are normally updated 
        asynchronously. This method bursts all protective domains and 
        assigns a position to each particle.

        Arguments:
            - t
                the time at which to synchronize the particles. Usually 
                you will want to use the current time of the simulator: 
                EGFRDSimulator.t.

        This method is called stop because it is usually called at the 
        end of a simulation. It is possible to call this method at an 
        earlier time. For example the Logger module does this, because 
        it needs to know the positions of the particles at each log 
        step.

        """
        if __debug__:
            log.info('stop at %s' % (FORMAT_DOUBLE % t))

        if self.t == t:
            return

        if t >= self.scheduler.top[1].time:
            raise RuntimeError('Stop time >= next event time.')

        if t < self.t:
            raise RuntimeError('Stop time < current time.')

        self.t = t

        non_single_list = []

        # first burst all Singles.
        for id, event in self.scheduler:
            obj = event.data
            if isinstance(obj, Pair) or isinstance(obj, Multi):
                non_single_list.append(obj)
            elif isinstance(obj, Single):
                if __debug__:
                    log.debug('burst %s, last_time= %s' % 
                              (obj, FORMAT_DOUBLE % obj.last_time))
                self.burst_single(obj)
            else:
                assert False, 'do not reach here'


        # then burst all Pairs and Multis.
        if __debug__:
            log.debug('burst %s' % non_single_list)
        self.burst_objs(non_single_list)

        self.dt = 0.0

    def step(self):
        """Execute one eGFRD step.

        """
        self.last_reaction = None

        if self.is_dirty:
            self.initialize()
            
        if __debug__:
            if int("0" + os.environ.get("ECELL_CHECK", ""), 10):
                self.check()
        
        self.step_counter += 1

        if __debug__:
            if self.scheduler.size == 0:
                raise RuntimeError('No particles in scheduler.')

        id, event = self.scheduler.pop()
        self.t, self.last_event = event.time, event

        if __debug__:
            domain_counts = self.count_domains()
            log.info('\n\n%d: t=%s dt=%s\t' %
                     (self.step_counter, FORMAT_DOUBLE % self.t,
                      FORMAT_DOUBLE % self.dt) + 
                     'Singles: %d, Pairs: %d, Multis: %d\n' % domain_counts + 
                     'event=#%d reactions=%d rejectedmoves=%d' %
                     (id, self.reaction_events, self.rejected_moves))
       
        for klass, f in self.dispatch:
            if isinstance(event.data, klass):
                f(self, event.data)

        if __debug__:
            if self.scheduler.size == 0:
                raise RuntimeError('Zero particles left.')

        next_time = self.scheduler.top[1].time
        self.dt = next_time - self.t

        # assert if not too many successive dt=0 steps occur.
        if __debug__:
            if self.dt == 0:
                self.zero_steps += 1
                if self.zero_steps >= max(self.scheduler.size * 3, 10):
                    raise RuntimeError('too many dt=zero steps. '
                                       'Simulator halted?')
            else:
                self.zero_steps = 0

    def create_single(self, pid_particle_pair):
        rts = self.network_rules.query_reaction_rule(pid_particle_pair[1].sid)
        domain_id = self.domain_id_generator()
        shell_id = self.shell_id_generator()

        # Get structure (region or surface).
        species = self.world.get_species(pid_particle_pair[1].sid)
        structure = self.world.get_structure(species.structure_id)

        # Create single. The type of the single that will be created 
        # depends on the structure (region or surface) this particle is 
        # in/on. Either SphericalSingle, PlanarSurfaceSingle, or 
        # CylindricalSurfaceSingle.
        single = create_default_single(domain_id, pid_particle_pair, 
                                       shell_id, rts, structure)

        single.initialize(self.t)
        self.move_shell(single.shell_id_shell_pair)
        self.domains[domain_id] = single

        if __debug__:
            # Used in __str__.
            single.world = self.world
        return single

    def create_pair(self, single1, single2, com, r0, shell_size):
        assert single1.dt == 0.0
        assert single2.dt == 0.0

        # Select 1 reaction type out of all possible reaction types.
        rts = self.network_rules.query_reaction_rule(
                single1.pid_particle_pair[1].sid,
                single2.pid_particle_pair[1].sid)
        k_array = numpy.add.accumulate([rt.k for rt in rts])
        k_max = k_array[-1]
        rnd = myrandom.uniform()
        i = numpy.searchsorted(k_array, rnd * k_max)
        rt = rts[i]
        # The probability for this reaction to happen is proportional to 
        # the sum of the rates of all the possible reaction types. 
        rt.ktot = k_max

        domain_id = self.domain_id_generator()
        shell_id = self.shell_id_generator()

        pos1 = single1.shell.shape.position
        pos2 = single2.shell.shape.position

        # Get structure (region or surface).
        species = self.world.get_species(single1.pid_particle_pair[1].sid)
        structure = self.world.get_structure(species.structure_id)

        # Create pair. The type of the pair that will be created depends
        # on the structure (region or surface) the particles are in/on.  
        # Either SphericalPair, PlanarSurfacePair, or 
        # CylindricalSurfacePair.
        pair = create_default_pair(domain_id, com, single1, single2, shell_id, 
                                   r0, shell_size, rt, structure)

        pair.initialize(self.t)

        self.move_shell(pair.shell_id_shell_pair)
        self.domains[domain_id] = pair

        if __debug__:
            # Used in __str__.
            pair.world = self.world

        return pair

    def create_multi(self):
        domain_id = self.domain_id_generator()
        if __debug__:
            try:
                # Option to make multis run faster for nicer visualization.
                dt_factor = DEFAULT_DT_FACTOR * self.bd_dt_factor
            except AttributeError:
                dt_factor = DEFAULT_DT_FACTOR 
        else:
            dt_factor = DEFAULT_DT_FACTOR
        multi = Multi(domain_id, self, dt_factor)
        self.domains[domain_id] = multi
        return multi

    def move_single(self, single, position, radius=None):
        self.move_single_shell(single, position, radius)
        self.move_single_particle(single, position)

    def move_single_shell(self, single, position, radius=None):
        if radius == None:
            # By default, don't change radius.
            radius = single.shell.shape.radius

        # Reuse shell_id and domain_id.
        shell_id = single.shell_id
        domain_id = single.domain_id

        # Replace shell.
        shell = single.create_new_shell(position, radius, domain_id)
        shell_id_shell_pair = (shell_id, shell) 

        single.shell_id_shell_pair = shell_id_shell_pair
        self.move_shell(shell_id_shell_pair)

    def move_single_particle(self, single, position):
        new_pid_particle_pair = (single.pid_particle_pair[0],
                          Particle(position,
                                   single.pid_particle_pair[1].radius,
                                   single.pid_particle_pair[1].D,
                                   single.pid_particle_pair[1].sid))
        single.pid_particle_pair = new_pid_particle_pair

        self.world.update_particle(new_pid_particle_pair)

    def get_container(self, shell):
        if type(shell) is SphericalShell:
            return self.containers[0]
        elif type(shell) is CylindricalShell:
            return self.containers[1]

    def remove_domain(self, obj):
        if __debug__:
            log.info("remove: %s" % obj)
        del self.domains[obj.domain_id]
        for shell_id, shell in obj.shell_list:
            container = self.get_container(shell)
            del container[shell_id]

    def move_shell(self, shell_id_shell_pair):
        shell = shell_id_shell_pair[1]
        container = self.get_container(shell)
        container.update(shell_id_shell_pair)

    def add_single_event(self, single):
        event_id = self.scheduler.add(
            DomainEvent(self.t + single.dt, single))
        if __debug__:
            log.info('add_event: %s, event=#%d, t=%s' %
                     (single.domain_id, event_id,
                      FORMAT_DOUBLE % (self.t + single.dt)))
        single.event_id = event_id

    def add_pair_event(self, pair):
        event_id = self.scheduler.add(
            DomainEvent(self.t + pair.dt, pair))
        if __debug__:
            log.info('add_event: %s, event=#%d, t=%s' %
                     (pair.domain_id, event_id,
                      FORMAT_DOUBLE % (self.t + pair.dt)))
        pair.event_id = event_id

    def add_multi_event(self, multi):
        event_id = self.scheduler.add(
            DomainEvent(self.t + multi.dt, multi))

        if __debug__:
            log.info('add_event: %s, event=#%d, t=%s' %
                     (multi.domain_id, event_id,
                      FORMAT_DOUBLE % (self.t + multi.dt)))
        multi.event_id = event_id

    def remove_event(self, event):
        if __debug__:
            log.info('remove_event: event=#%d' % event.event_id)
        del self.scheduler[event.event_id]

    def update_single_event(self, t, single):
        if __debug__:
            log.info('update_event: %s, event=#%d, t=%s' %
                     (single.domain_id, single.event_id, FORMAT_DOUBLE % t))
        self.scheduler.update((single.event_id, DomainEvent(t, single)))

    def update_multi_event(self, t, multi):
        if __debug__:
            log.info('update_event: %s, event=#%d, t=%s' %
                     (multi.domain_id, multi.event_id, FORMAT_DOUBLE % t))
        self.scheduler.update((multi.event_id, DomainEvent(t, multi)))

    def burst_obj(self, obj):
        if __debug__:
            log.info('burst_obj: %s' % obj)

        if isinstance(obj, Single):
            # TODO. Compare with gfrd.
            obj = self.burst_single(obj)
            bursted = [obj, ]
        elif isinstance(obj, Pair):  # Pair
            single1, single2 = self.burst_pair(obj)
            # Don't schedule events in burst/propagate_pair, because 
            # scheduling is different after a single reaction in 
            # fire_pair.
            self.add_single_event(single1)
            self.add_single_event(single2)
            self.remove_event(obj)
            bursted = [single1, single2]
        else:  # Multi
            bursted = self.burst_multi(obj)
            self.remove_event(obj)

        if __debug__:
            log.info('bursted = %s' % ',\n\t  '.join(str(i) for i in bursted))

        return bursted

    def burst_objs(self, objs):
        bursted = []
        for obj in objs:
            b = self.burst_obj(obj)
            bursted.extend(b)

        return bursted

    def clear_volume(self, pos, radius, ignore=[]):
        neighbors = self.get_neighbors_within_radius_no_sort(pos, radius,
                                                             ignore)
        return self.burst_objs(neighbors)

    def burst_non_multis(self, neighbors):
        bursted = []

        for obj in neighbors:
            if not isinstance(obj, Multi):
                b = self.burst_obj(obj)
                bursted.extend(b)
            else:
                bursted.append(obj)

        return bursted

    def fire_single_reaction(self, single):
        reactant_species_radius = single.pid_particle_pair[1].radius
        oldpos = single.pid_particle_pair[1].position
        current_surface = single.surface
        
        rt = single.draw_reaction_rule()

        if len(rt.products) == 0:
            
            self.world.remove_particle(single.pid_particle_pair[0])

            self.last_reaction = (rt, (single.pid_particle_pair[1], None), [])

            
        elif len(rt.products) == 1:
            
            product_species = self.world.get_species(rt.products[0])

            if reactant_species_radius < product_species.radius:
                self.clear_volume(oldpos, product_species.radius)

            if self.world.check_overlap((oldpos, product_species.radius),
                                        single.pid_particle_pair[0]):
                if __debug__:
                    log.info('no space for product particle.')
                raise NoSpace()

            self.world.remove_particle(single.pid_particle_pair[0])
            newparticle = self.world.new_particle(product_species.id, oldpos)
            newsingle = self.create_single(newparticle)
            if __debug__:
                log.info('product = %s' % newsingle)
            self.add_single_event(newsingle)

            self.last_reaction = (rt, (single.pid_particle_pair[1], None),
                                  [newparticle])


            
        elif len(rt.products) == 2:
            product_species1 = self.world.get_species(rt.products[0])
            product_species2 = self.world.get_species(rt.products[1])
            
            D1 = product_species1.D
            D2 = product_species2.D
            D12 = D1 + D2
            
            particle_radius1 = product_species1.radius
            particle_radius2 = product_species2.radius
            particle_radius12 = particle_radius1 + particle_radius2

            # clean up space.
            rad = max(particle_radius12 * (D1 / D12) + particle_radius1,
                      particle_radius12 * (D2 / D12) + particle_radius2)

            self.clear_volume(oldpos, rad)

            for _ in range(self.dissociation_retry_moves):
                vector = _random_vector(current_surface, particle_radius12 *
                                        MINIMAL_SEPARATION_FACTOR, self.rng)
            
                # place particles according to the ratio D1:D2
                # this way, species with D=0 doesn't move.
                # FIXME: what if D1 == D2 == 0?

                while 1:
                    newpos1 = oldpos + vector * (D1 / D12)
                    newpos2 = oldpos - vector * (D2 / D12)
                    newpos1 = self.world.apply_boundary(newpos1)
                    newpos2 = self.world.apply_boundary(newpos2)

                    if(self.world.distance(newpos1, newpos2) >= 
                       particle_radius12):
                        break

                    vector *= 1.0 + 1e-7


                # accept the new positions if there is enough space.
                if(not self.world.check_overlap((newpos1, particle_radius1),
                                                 single.pid_particle_pair[0])
                   and
                   not self.world.check_overlap((newpos2, particle_radius2),
                                                 single.pid_particle_pair[0])):
                    break
            else:
                if __debug__:
                    log.info('no space for product particles.')
                raise NoSpace()

            self.world.remove_particle(single.pid_particle_pair[0])

            particle1 = self.world.new_particle(product_species1.id, newpos1)
            particle2 = self.world.new_particle(product_species2.id, newpos2)
            newsingle1 = self.create_single(particle1)
            newsingle2 = self.create_single(particle2)

            if __debug__:
                log.info('product1 = %s\nproduct2 = %s' % 
                     (newsingle1, newsingle2))

            self.add_single_event(newsingle1)
            self.add_single_event(newsingle2)

            self.last_reaction = (rt, (single.pid_particle_pair[1], None),
                                  [particle1, particle2])


        else:
            raise RuntimeError('num products >= 3 not supported.')

        self.reaction_events += 1

    def propagate_single(self, single):
        # The difference between a burst and a propagate is that a burst 
        # always takes place before the actual scheduled event for the 
        # single, while propagate_single can be called for an escape event.

        # Another subtle difference is that burst_single always 
        # reschedules (update_event) the single, while just calling 
        # propagate does not.  So whoever calls propagate_single 
        # directly should reschedule the single afterwards.
        if __debug__:
            log.debug("single.dt=%s, single.last_time=%s, self.t=%s" %
                      (FORMAT_DOUBLE % single.dt,
                       FORMAT_DOUBLE % single.last_time,
                       FORMAT_DOUBLE % self.t))

        newpos = single.draw_new_position(single.dt, single.event_type) 
        newpos = self.world.apply_boundary(newpos)

        if __debug__:
            log.debug("propagate %s: %s => %s" %
                      (single, single.pid_particle_pair[1].position, newpos))

            if self.world.check_overlap((newpos,
                                        single.pid_particle_pair[1].radius),
                                        single.pid_particle_pair[0]):
                raise RuntimeError('propagate_single: check_overlap failed.')

        if(single.event_type == EventType.SINGLE_REACTION and
           single.event_type != EventType.BURST):
            # SINGLE_REACTION, and not a burst. No need to update, single is 
            # removed anyway.
            self.move_single_particle(single, newpos)
            return single
        else:
            # Todo. if isinstance(single, InteractionSingle):
            single.initialize(self.t)
            self.move_single(single, newpos,
                             single.pid_particle_pair[1].radius)

            return single

    def fire_single(self, single):
        assert abs(single.dt + single.last_time - self.t) <= 1e-18 * self.t

        # Reaction.
        if single.event_type == EventType.SINGLE_REACTION:
            if __debug__:
                log.info('%s' % single.event_type)
                log.info('reactant = %s' % single)

            self.single_steps[single.event_type] += 1


            single = self.propagate_single(single)

            try:
                self.remove_domain(single)
                self.fire_single_reaction(single)
            except NoSpace:
                self.reject_single_reaction(single)

            return

        if single.event_type == EventType.IV_EVENT:
            # Draw actual pair event for iv at very last minute.
            single.event_type = single.draw_iv_event_type()
            self.interaction_steps[single.event_type] += 1
        else:
            self.single_steps[single.event_type] += 1

        if __debug__:
            log.info('%s' % single.event_type)
            log.info('single = %s' % single)

        # Handle immobile case first.
        if single.getD() == 0:
            # no propagation, just calculate next reaction time.
            single.dt, single.event_type = single.determine_next_event() 
            single.last_time = self.t
            self.add_single_event(single)
            return
        
        if single.dt != 0.0:
            # Propagate this particle to the exit point on the shell.
            single = self.propagate_single(single)

        singlepos = single.shell.shape.position

        # (2) Clear volume.

        min_shell = single.pid_particle_pair[1].radius * \
                    self.SINGLE_SHELL_FACTOR

        intruders, closest, closest_distance = \
            self.get_intruders(singlepos, min_shell,
                               ignore=[single.domain_id, ])

        if __debug__:
            log.debug("intruders: %s, closest: %s (dist=%s)" %
                      (', '.join(str(i) for i in intruders),
                       closest, FORMAT_DOUBLE % closest_distance))

        if intruders:
            burst = self.burst_non_multis(intruders)

            obj = self.form_pair_or_multi(single, burst)

            if obj:
                return

            # if nothing was formed, recheck closest and restore shells.
            burst = uniq(burst)

            closest, closest_distance = \
                self.get_closest_obj(singlepos, ignore=[single.domain_id],
                                     ignores=[single.surface.id])
            self.update_single(single, closest, closest_distance)
            for s in burst:
                if not isinstance(s, Single):
                    continue
                assert s.is_reset()
                closest, closest_distance = self.get_closest_obj(
                    s.shell.shape.position, ignore=[s.domain_id],
                    ignores=[s.surface.id])

                self.update_single(s, closest, closest_distance)
                self.update_single_event(self.t + s.dt, s)
                if __debug__:
                    log.debug('restore shell %s radius %s dt %s\n'
                              'closest %s distance %s' %
                              (s, FORMAT_DOUBLE % s.shell.shape.radius,
                               FORMAT_DOUBLE % s.dt, closest,
                               FORMAT_DOUBLE % closest_distance))
        else:
            self.update_single(single, closest, closest_distance)
            
        if __debug__:
            log.info('updated shell: (%s,\n  Shell(%s, %s)' %
                     (single.shell_id, single.shell.did,
                      single.shell.shape.show(PRECISION)))

        self.add_single_event(single)
        return

    def reject_single_reaction(self, single):
        if __debug__:
            log.info('single reaction; placing product failed.')
        self.domains[single.domain_id] = single
        self.move_shell(single.shell_id_shell_pair)
        self.rejected_moves += 1
        single.initialize(self.t)
        self.add_single_event(single)

    def calculate_single_shell_size(self, single, closest, 
                                 distance, shell_distance):
        assert isinstance(closest, Single)

        min_radius1 = single.pid_particle_pair[1].radius
        D1 = single.getD()

        if D1 == 0:
            return min_radius1

        D2 = closest.getD()
        min_radius2 = closest.pid_particle_pair[1].radius
        min_radius12 = min_radius1 + min_radius2
        sqrtD1 = math.sqrt(D1)
            
        shell_size = min(sqrtD1 / (sqrtD1 + math.sqrt(D2))
                        * (distance - min_radius12) + min_radius1,
                        shell_distance / SAFETY)
        if shell_size < min_radius1:
            shell_size = min_radius1

        return shell_size

    def update_single(self, single, closest, distance_to_shell): 
        # Todo. assert not isinstance(single, InteractionSingle)

        singlepos = single.shell.shape.position
        if isinstance(closest, Single):
            closestpos = closest.shell.shape.position
            distance_to_closest = self.world.distance(singlepos, closestpos)
            new_shell_size = self.calculate_single_shell_size(single, closest, 
                                                      distance_to_closest,
                                                      distance_to_shell)
        else:  # Pair or Multi or Surface
            new_shell_size = distance_to_shell / SAFETY
            new_shell_size = max(new_shell_size,
                                 single.pid_particle_pair[1].radius)

        new_shell_size = min(new_shell_size, self.get_max_shell_size())

        # Resize shell, don't change position.
        # Note: this should be done before determine_next_event.
        self.move_single_shell(single, singlepos, new_shell_size)        

        single.dt, single.event_type = single.determine_next_event()
        single.last_time = self.t

    def fire_pair(self, pair):
        assert self.check_obj(pair)

        single1 = pair.single1
        single2 = pair.single2
        particle1 = single1.pid_particle_pair
        particle2 = single2.pid_particle_pair
        pos1 = particle1[1].position
        pos2 = particle2[1].position
        
        if pair.event_type == EventType.IV_EVENT:
            # Draw actual pair event for iv at very last minute.
            r0 = self.world.distance(pos1, pos2)
            pair.event_type = pair.draw_iv_event_type(r0)

        self.pair_steps[pair.event_type] += 1

        if __debug__:
            log.info('FIRE PAIR: %s' % pair.event_type)
            log.info('single1 = %s' % pair.single1)
            log.info('single2 = %s' % pair.single2)


        old_com = pair.com

        # Four cases:
        #  1. Single reaction
        #  2. Pair reaction
        #  3a. IV escape
        #  3b. com escape

        #
        # 1. Single reaction
        #
        if pair.event_type == EventType.SINGLE_REACTION:
            reactingsingle = pair.reactingsingle

            if reactingsingle == single1:
                theothersingle = single2
            else:
                theothersingle = single1

            self.burst_pair(pair)

            self.add_single_event(theothersingle)

            if __debug__:
                log.info('reactant = %s' % reactingsingle)
            try:
                self.remove_domain(reactingsingle)
                self.fire_single_reaction(reactingsingle)
            except NoSpace:
                self.reject_single_reaction(reactingsingle)

            return
        
        #
        # 2. Pair reaction
        #
        if pair.event_type == EventType.IV_REACTION:
            self.world.remove_particle(single1.pid_particle_pair[0])
            self.world.remove_particle(single2.pid_particle_pair[0])

            if len(pair.rt.products) == 1:
                species3 = self.world.get_species(pair.rt.products[0])

                # calculate new R
                event_type = pair.event_type
                new_com = pair.draw_new_com(pair.dt, event_type)

                if __debug__:
                    shell_size = pair.get_shell_size()
                    assert self.world.distance(old_com, new_com) < \
                           shell_size - species3.radius

                new_com = self.world.apply_boundary(new_com)

                particle = self.world.new_particle(species3.id, new_com)
                product = self.create_single(particle)
                self.add_single_event(product)

                self.reaction_events += 1

                self.last_reaction = (pair.rt, (particle1, particle2),
                                      [particle])
            elif len(pair.rt.products) == 0:
                product = []
            else:
                raise NotImplementedError('num products >= 2 not supported.')

            if __debug__:
                log.info('product = %s' % product)
            self.remove_domain(pair)

            return

        #
        # 3a. Escaping through a_r.
        # 3b. Escaping through a_R.
        #
        elif(pair.event_type == EventType.IV_ESCAPE or
             pair.event_type == EventType.COM_ESCAPE):
            dt = pair.dt
            event_type = pair.event_type
            single1, single2 = self.propagate_pair(pair, dt, event_type)
            self.add_single_event(single1)
            self.add_single_event(single2)
        else:
            raise SystemError('Bug: invalid event_type.')

        return

    def fire_multi(self, multi):
        self.multi_steps[3] += 1  # multi_steps[3]: total multi steps
        multi.step()

        if __debug__:
            log.info('FIRE MULTI: %s' % multi.last_event)

        if(multi.last_event == EventType.MULTI_UNIMOLECULAR_REACTION or
           multi.last_event == EventType.MULTI_BIMOLECULAR_REACTION):
            self.reaction_events += 1
            self.last_reaction = multi.last_reaction

        if multi.last_event is not None:
            self.break_up_multi(multi)
            self.multi_steps[multi.last_event] += 1
        else:
            self.add_multi_event(multi)

    def break_up_multi(self, multi):
        self.remove_domain(multi)

        singles = []
        for pid_particle_pair in multi.particles:
            single = self.create_single(pid_particle_pair)
            self.add_single_event(single)
            singles.append(single)

        return singles

    def burst_multi(self, multi):
        #multi.sim.sync()
        assert isinstance(multi, Multi)
        singles = self.break_up_multi(multi)

        return singles

    def burst_single(self, single):
        assert self.t >= single.last_time
        assert self.t <= single.last_time + single.dt

        oldpos = single.shell.shape.position
        old_shell_size = single.get_shell_size()

        particle_radius = single.pid_particle_pair[1].radius

        # Override dt, burst happens before single's scheduled event.
        single.dt = self.t - single.last_time
        # Override event_type. Always call gf.drawR on BURST.
        single.event_type = EventType.BURST
        newsingle = self.propagate_single(single)

        newpos = newsingle.pid_particle_pair[1].position
        assert self.world.distance(newpos, oldpos) <= \
               old_shell_size - particle_radius
        # Displacement check is in NonInteractionSingle.draw_new_position.

        # Todo. if isinstance(single, InteractionSingle):
        self.update_single_event(self.t, single)

        assert newsingle.shell.shape.radius == particle_radius

        # Returned single is different from original single in the case 
        # of an InteractionSingle only.
        return newsingle

    def burst_pair(self, pair):
        if __debug__:
            log.debug('burst_pair: %s', pair)

        assert self.t >= pair.last_time
        assert self.t <= pair.last_time + pair.dt

        dt = self.t - pair.last_time 
        # Override event_type. Always call sgf.drawR and pgf.drawR on BURST.
        event_type = EventType.BURST
        single1, single2 = self.propagate_pair(pair, dt, event_type)

        return single1, single2

    def propagate_pair(self, pair, dt, event_type):
        single1 = pair.single1
        single2 = pair.single2

        particle1 = single1.pid_particle_pair
        particle2 = single2.pid_particle_pair

        pos1 = particle1[1].position
        pos2 = particle2[1].position

        if dt > 0.0:
            D1 = particle1[1].D
            D2 = particle2[1].D

            pos2t = self.world.cyclic_transpose(pos2, pos1)
            old_inter_particle = pos2t - pos1
            r0 = self.world.distance(pos1, pos2)
            assert feq(r0, length(old_inter_particle))

            old_com = pair.com

            newpos1, newpos2 = pair.draw_new_positions(dt, r0, 
                                                     old_inter_particle, 
                                                     event_type)

            newpos1 = self.world.apply_boundary(newpos1)
            newpos2 = self.world.apply_boundary(newpos2)
            assert not self.world.check_overlap((newpos1, particle1[1].radius),
                                                particle1[0], particle2[0])
            assert not self.world.check_overlap((newpos2, particle2[1].radius),
                                                particle1[0], particle2[0])
            assert self.check_pair_pos(pair, newpos1, newpos2, old_com,
                                       pair.get_shell_size())
        else:
            newpos1 = particle1[1].position
            newpos2 = particle2[1].position

        if __debug__:
            log.debug("fire_pair: #1 { %s: %s => %s }" %
                      (single1, pos1, newpos1))
            log.debug("fire_pair: #2 { %s: %s => %s }" %
                      (single2, str(pos2), str(newpos2)))

        single1.initialize(self.t)
        single2.initialize(self.t)
        
        self.remove_domain(pair)
        assert single1.domain_id not in self.domains
        assert single2.domain_id not in self.domains
        self.domains[single1.domain_id] = single1
        self.domains[single2.domain_id] = single2
        self.move_single(single1, newpos1, particle1[1].radius)
        self.move_single(single2, newpos2, particle2[1].radius)

        if __debug__:
            container = self.get_container(single1.shell)
            assert container[single1.shell_id].shape.radius == \
                   single1.shell.shape.radius
            assert container[single2.shell_id].shape.radius == \
                   single2.shell.shape.radius

            if type(single1.shell) is CylindricalShell:
                assert container[single1.shell_id].shape.half_length == \
                       single1.shell.shape.half_length
                assert container[single2.shell_id].shape.half_length == \
                       single2.shell.shape.half_length

        assert single1.shell.shape.radius == particle1[1].radius
        assert single2.shell.shape.radius == particle2[1].radius

        assert self.check_obj(single1)
        assert self.check_obj(single2)

        return single1, single2

    def form_pair_or_multi(self, single, neighbors):
        assert neighbors

        singlepos = single.shell.shape.position

        # sort burst neighbors by distance
        dists = self.obj_distance_array(singlepos, neighbors)
        if len(dists) >= 2:
            n = dists.argsort()
            dists = dists.take(n)
            neighbors = numpy.take(neighbors, n)

        # First, try forming a Pair.
        if isinstance(neighbors[0], Single):
            obj = self.form_pair(single, singlepos,
                                 neighbors[0], neighbors[1:])
            if obj:
                return obj

        # If a Pair is not formed, then try forming a Multi.
        obj = self.form_multi(single, neighbors, dists)
        if obj:
            return obj


    def form_pair(self, single1, pos1, single2, burst):
        if __debug__:
           log.debug('trying to form Pair(%s, %s)' %
                     (single1.pid_particle_pair, single2.pid_particle_pair))

        assert single1.is_reset()
        assert single2.is_reset()

        # 1. Determine min shell size.
        radius1 = single1.pid_particle_pair[1].radius
        radius2 = single2.pid_particle_pair[1].radius

        sigma = radius1 + radius2

        D1 = single1.pid_particle_pair[1].D
        D2 = single2.pid_particle_pair[1].D
        D12 = D1 + D2

        assert (pos1 - single1.shell.shape.position).sum() == 0
        pos2 = single2.shell.shape.position
        r0 = self.world.distance(pos1, pos2)
        distance_from_sigma = r0 - sigma
        assert distance_from_sigma >= 0, \
            'distance_from_sigma (pair gap) between %s and %s = %s < 0' % \
            (single1, single2, FORMAT_DOUBLE % distance_from_sigma)

        shell_size1 = r0 * D1 / D12 + radius1
        shell_size2 = r0 * D2 / D12 + radius2
        shell_size_margin1 = radius1 * 2
        shell_size_margin2 = radius2 * 2
        shell_size_with_margin1 = shell_size1 + shell_size_margin1
        shell_size_with_margin2 = shell_size2 + shell_size_margin2
        if shell_size_with_margin1  >= shell_size_with_margin2:
            min_shell_size = shell_size1
            shell_size_margin = shell_size_margin1
        else:
            min_shell_size = shell_size2
            shell_size_margin = shell_size_margin2

        # 2. Check if min shell size not larger than max shell size or 
        # sim cell size.
        com = self.world.calculate_pair_CoM(pos1, pos2, D1, D2)
        com = self.world.apply_boundary(com)
        min_shell_size_with_margin = min_shell_size + shell_size_margin
        max_shell_size = min(self.get_max_shell_size(),
                             distance_from_sigma * 100 +
                             sigma + shell_size_margin)

        if min_shell_size_with_margin >= max_shell_size:
            if __debug__:
                log.debug('%s not formed: min_shell_size %s >='
                          'max_shell_size %s' %
                          ('Pair(%s, %s)' % (single1.pid_particle_pair[0], 
                                             single2.pid_particle_pair[0]),
                           FORMAT_DOUBLE % min_shell_size_with_margin,
                           FORMAT_DOUBLE % max_shell_size))
            return None

        # 3. Check if bursted Singles not too close.
        # The simple check for closest below could miss
        # some of them, because sizes of these Singles for this
        # distance check has to include SINGLE_SHELL_FACTOR, while
        # these burst objects have zero mobility radii.  This is not
        # beautiful, a cleaner framework may be possible.

        closest, closest_shell_distance = None, numpy.inf
        for b in burst:
            if isinstance(b, Single):
                bpos = b.shell.shape.position
                d = self.world.distance(com, bpos) - \
                    b.pid_particle_pair[1].radius * self.SINGLE_SHELL_FACTOR
                if d < closest_shell_distance:
                    closest, closest_shell_distance = b, d

        if closest_shell_distance <= min_shell_size_with_margin:
            if __debug__:
                log.debug('%s not formed: squeezed by burst neighbor %s' %
                          ('Pair(%s, %s)' % (single1.pid_particle_pair[0], 
                                             single2.pid_particle_pair[0]),
                           closest))
            return None

        assert closest_shell_distance > 0

        # 4. Determine shell size and check if closest object not too 
        # close (squeezing).
        c, d = self.get_closest_obj(com, ignore=[single1.domain_id,
                                                 single2.domain_id],
                                    ignores=[single1.surface.id])
        if d < closest_shell_distance:
            closest, closest_shell_distance = c, d

        if __debug__:
            log.debug('Pair closest neighbor: %s %s, '
                      'min_shell_with_margin %s' %
                      (closest, FORMAT_DOUBLE % closest_shell_distance,
                       FORMAT_DOUBLE % min_shell_size_with_margin))

        assert closest_shell_distance > 0

        if isinstance(closest, Single):

            D_closest = closest.pid_particle_pair[1].D
            D_tot = D_closest + D12
            closest_particle_distance = self.world.distance(
                    com, closest.pid_particle_pair[1].position)

            closest_min_radius = closest.pid_particle_pair[1].radius
            closest_min_shell = closest_min_radius * self.SINGLE_SHELL_FACTOR

            # options for shell size:
            # a. ideal shell size
            # b. closest shell is from a bursted single
            # c. closest shell is closer than ideal shell size 
            shell_size = min((D12 / D_tot) *
                            (closest_particle_distance - min_shell_size 
                             - closest_min_radius) + min_shell_size,
                            closest_particle_distance - closest_min_shell,
                            closest_shell_distance)

            shell_size /= SAFETY
            assert shell_size < closest_shell_distance

        else:
            assert isinstance(closest, (Pair, Multi, None.__class__))

            shell_size = closest_shell_distance / SAFETY

        if shell_size <= min_shell_size_with_margin:
            if __debug__:
                log.debug('%s not formed: squeezed by %s' %
                          ('Pair(%s, %s)' % (single1.pid_particle_pair[0], 
                                             single2.pid_particle_pair[0]),
                           closest))
            return None


        # 5. Check if singles would not be better.
        d1 = self.world.distance(com, pos1)
        d2 = self.world.distance(com, pos2)

        if shell_size < max(d1 + single1.pid_particle_pair[1].radius *
                            self.SINGLE_SHELL_FACTOR, \
                            d2 + single2.pid_particle_pair[1].radius * \
                            self.SINGLE_SHELL_FACTOR) * 1.3:
            if __debug__:
                log.debug('%s not formed: singles are better' %
                          'Pair(%s, %s)' % (single1.pid_particle_pair[0], 
                                            single2.pid_particle_pair[0]))
            return None

        # 6. Ok, Pair makes sense. Create one.
        shell_size = min(shell_size, max_shell_size)

        pair = self.create_pair(single1, single2, com, r0, shell_size)

        pair.dt, pair.event_type, pair.reactingsingle = \
            pair.determine_next_event(r0)

        assert pair.dt >= 0

        self.last_time = self.t

        self.remove_domain(single1)
        self.remove_domain(single2)

        # single1 will be removed by the scheduler.
        self.remove_event(single2)

        assert closest_shell_distance == numpy.inf or \
               shell_size < closest_shell_distance
        assert shell_size >= min_shell_size_with_margin
        assert shell_size <= max_shell_size

        if __debug__:
            log.info('%s,\ndt=%s, r0=%s, shell_size=%s, '
                     'closest_shell_distance=%s,\nclosest = %s' %
                     (pair, FORMAT_DOUBLE % pair.dt, FORMAT_DOUBLE % r0, 
                      FORMAT_DOUBLE % shell_size, 
                      FORMAT_DOUBLE % closest_shell_distance, closest))

        assert self.check_obj(pair)
        self.add_pair_event(pair)

        return pair
    

    def form_multi(self, single, neighbors, dists):

        min_shell = single.pid_particle_pair[1].radius * \
                    (1.0 + self.MULTI_SHELL_FACTOR)
        # Multis shells need to be contiguous.
        if dists[0] > min_shell:
            return None

        neighbors = [neighbors[i] for i in (dists <= min_shell).nonzero()[0]]

        closest = neighbors[0]

        # if the closest to this Single is a Single, create a new Multi
        if isinstance(closest, Single):

            multi = self.create_multi()
            self.add_to_multi(single, multi)
            self.remove_domain(single)
            for neighbor in neighbors:
                self.add_to_multi_recursive(neighbor, multi)

            multi.initialize(self.t)
            
            self.add_multi_event(multi)

            return multi

        # if the closest to this Single is a Multi, reuse the Multi.
        elif isinstance(closest, Multi):

            multi = closest
            self.add_to_multi(single, multi)
            self.remove_domain(single)
            for neighbor in neighbors[1:]:
                self.add_to_multi_recursive(neighbor, multi)

            multi.initialize(self.t)

            self.update_multi_event(self.t + multi.dt, multi)

            return multi


        assert False, 'do not reach here'


    def add_to_multi_recursive(self, obj, multi):
        if isinstance(obj, Single):
            if multi.has_particle(obj.pid_particle_pair[0]):
                # Already in the Multi.
                return
            assert obj.is_reset()
            objpos = obj.shell.shape.position
            
            self.add_to_multi(obj, multi)
            self.remove_domain(obj)
            self.remove_event(obj)

            radius = obj.pid_particle_pair[1].radius * \
                (1.0 + self.MULTI_SHELL_FACTOR)
            neighbors = self.get_neighbors_within_radius_no_sort(
                    objpos, radius, ignore=[obj.domain_id])

            burst = self.burst_non_multis(neighbors)
            neighbor_dists = self.obj_distance_array(objpos, burst)
            neighbors = [burst[i] for i
                                  in (neighbor_dists <= radius).nonzero()[0]]

            for obj in neighbors:
                self.add_to_multi_recursive(obj, multi)

        elif isinstance(obj, Multi):
            for pp in multi.particles:
                if obj.has_particle(pp[0]):
                    if __debug__:
                        log.debug('%s already added. skipping.' % obj)
                    break
            else:
                self.merge_multis(obj, multi)
        else:
            assert False, 'do not reach here.'  # Pairs are burst

    def new_spherical_shell(self, domain_id, pos, size):
        shell_id_shell_pair = (
            self.shell_id_generator(),
            SphericalShell(domain_id, Sphere(pos, size)))
        self.move_shell(shell_id_shell_pair)
        return shell_id_shell_pair

    def add_to_multi(self, single, multi):
        if __debug__:
            log.info('add to multi:\n  %s\n  %s' % (single, multi))

        sid_shell_pair = self.new_spherical_shell(
            multi.domain_id,
            single.pid_particle_pair[1].position,
            single.pid_particle_pair[1].radius * \
                (1.0 + self.MULTI_SHELL_FACTOR))
        multi.add_shell(sid_shell_pair)
        multi.add_particle(single.pid_particle_pair)

    def merge_multis(self, multi1, multi2):
        # merge multi1 into multi2. multi1 will be removed.
        if __debug__:
            log.info('merging %s to %s' % (multi1.domain_id, multi2.domain_id))
            log.info('  %s' % multi1)
            log.info('  %s' % multi2)

            try:
                particle_of_multi1 = iter(multi1.particle_container).next()
                assert particle_of_multi1[0] not in \
                        multi2.particle_container
            except:
                pass

        for sid_shell_pair in multi1.shell_list:
            sid_shell_pair[1].did = multi2.domain_id
            self.move_shell(sid_shell_pair)
            multi2.add_shell(sid_shell_pair)

        for pid_particle_pair in multi1.particles:
            multi2.add_particle(pid_particle_pair)

        del self.domains[multi1.domain_id]
        self.remove_event(multi1)

    def get_neighbors_within_radius_no_sort(self, pos, radius, ignore=[]):
        # Get neighbor domains within given radius.
        #
        # ignore: domain ids.
        #
        # Only returns neighbors, not the distances towards their 
        # shells. Can for example be used to try to clear all objects 
        # from a certain volume.

        for container in self.containers:
            result = container.get_neighbors_within_radius(pos, radius)
            # result = [((shell_id_shell_pair), distance), ]
            # Since a domain can have more than 1 shell (multis for 
            # example), and for each shell there is an entry in the 
            # shell container, we make sure each domain occurs only once 
            # in the returned list here.
            for did in uniq(s[0][1].did for s in result):
                if did not in ignore:
                    yield self.domains[did]

    def get_intruders(self, position, radius, ignore):
        intruders = []   # intruders are domains within radius
        closest_domain = None   # closest domain, excluding intruders.
        closest_distance = numpy.inf # distance to the shell of the closest.

        seen = set(ignore)
        for container in self.containers:
            neighbors = container.get_neighbors(position)
            for n in neighbors:
                domain_id = n[0][1].did
                distance = n[1]
                if distance > radius:
                    if distance < closest_distance:
                        # This is domain (the first one for this 
                        # container) that has a shell that is more than 
                        # radius away from pos.  If it is closer than 
                        # the closest such one we found so far: store 
                        # it. Always break out of the inner for loop and 
                        # check the other containers.
                        closest_domain = self.domains[domain_id]
                        closest_distance = distance
                        break
                    else:
                        break
                elif domain_id not in seen:
                    # Since a domain can have more than 1 shell (multis 
                    # for example), and for each shell there is an entry 
                    # in the shell container, we make sure each domain 
                    # occurs only once in the returned list here.
                    seen.add(domain_id)
                    intruders.append(self.domains[domain_id])

        return intruders, closest_domain, closest_distance

    def get_closest_obj(self, pos, ignore=[], ignores=[]):
        # ignore: domain ids.
        closest_domain = None
        closest_distance = numpy.inf

        for container in self.containers:
            result = container.get_neighbors(pos)

            for shell_id_shell_pair, distance in result:
                domain_id = shell_id_shell_pair[1].did 

                if domain_id not in ignore and distance < closest_distance:
                    domain = self.domains[domain_id]
                    closest_domain, closest_distance = domain, distance
                    # Found yet a closer domain. Break out of inner for 
                    # loop and check other containers.
                    break   

        surface, distance = get_closest_surface(self.world, pos, ignores)

        if distance < closest_distance:
            return surface, distance
        else:
            return closest_domain, closest_distance

    def obj_distance(self, pos, obj):
        return min(self.world.distance(shell.shape, pos)
                   for i, (_, shell) in enumerate(obj.shell_list))

    def obj_distance_array(self, pos, objs):
        dists = numpy.array([self.obj_distance(pos, obj) for obj in objs])
        return dists
            

    #
    # statistics reporter
    #

    def print_report(self, out=None):
        """Print various statistics about the simulation.
        
        Arguments:
            - None

        """
        report = '''
t = %.16g
steps = %d 
\tSingle:\t%d\t(escape: %d, reaction: %d)
\tInteraction: %d\t(escape: %d, interaction: %d)
\tPair:\t%d\t(escape r: %d, R: %d, reaction pair: %d, single: %d)
\tMulti:\t%d\t(escape: %d, reaction pair: %d, single: %d)
total reactions = %d
rejected moves = %d
''' \
            % (self.t, self.step_counter,
               numpy.array(self.single_steps.values()).sum(),
               self.single_steps[EventType.SINGLE_ESCAPE],
               self.single_steps[EventType.SINGLE_REACTION],
               numpy.array(self.interaction_steps.values()).sum(),
               self.interaction_steps[EventType.IV_ESCAPE],
               self.interaction_steps[EventType.IV_INTERACTION],
               numpy.array(self.pair_steps.values()).sum(),
               self.pair_steps[EventType.IV_ESCAPE],
               self.pair_steps[EventType.COM_ESCAPE],
               self.pair_steps[EventType.IV_REACTION],
               self.pair_steps[EventType.SINGLE_REACTION],
               self.multi_steps[3], # total multi steps
               self.multi_steps[EventType.MULTI_ESCAPE],
               self.multi_steps[EventType.MULTI_BIMOLECULAR_REACTION],
               self.multi_steps[EventType.MULTI_UNIMOLECULAR_REACTION],
               self.reaction_events,
               self.rejected_moves
               )

        print >> out, report

    #
    # consistency checkers
    #

    def check_obj(self, obj):
        obj.check()

        for shell_id, shell in obj.shell_list:
            if not isinstance(obj, Multi):
                ignores = [obj.surface.id]
            else:
                ignores = []
            closest, distance = self.get_closest_obj(shell.shape.position,
                                                     ignore=[obj.domain_id],
                                                     ignores=ignores)
            if(type(obj) is CylindricalSurfaceSingle or
               type(obj) is CylindricalSurfacePair):
                shell_size = shell.shape.half_length
            else:
                shell_size = shell.shape.radius

            assert shell_size <= self.get_user_max_shell_size(), \
                '%s shell size larger than user-set max shell size' % \
                str(shell_id)

            assert shell_size <= self.get_max_shell_size(), \
                '%s shell size larger than simulator cell size / 2' % \
                str(shell_id)

            assert distance - shell_size >= 0.0, \
                '%s overlaps with %s. (shell: %s, dist: %s, diff: %s.' % \
                (str(obj), str(closest), FORMAT_DOUBLE % shell_size,
                 FORMAT_DOUBLE % distance,
                 FORMAT_DOUBLE % (distance - shell_size))

        return True

    def check_obj_for_all(self):
        for id, event in self.scheduler:
            self.check_obj(event.data)

    def check_event_stoichiometry(self):
        event_population = 0
        for id, event in self.scheduler:
            event_population += event.data.multiplicity

        if self.world.num_particles != event_population:
            raise RuntimeError('population %d != event_population %d' %
                               (population, event_population))

    def check_shell_matrix(self):
        did_map = {}
        shell_map = {}
        for container in self.containers:
            if self.world.world_size != container.world_size:
                raise RuntimeError('self.world.world_size != '
                                   'container.world_size')
            for shell_id, shell in container:
                did_map.setdefault(shell.did, []).append(shell_id)
                shell_map[shell_id] = shell

        shell_population = 0
        for id, event in self.scheduler:
            shell_population += event.data.num_shells
            shell_ids = did_map[event.data.domain_id]
            if len(shell_ids) != event.data.num_shells:
                diff = set(sid for (sid, _)
                               in event.data.shell_list).difference(shell_ids)
                for sid in diff:
                    print shell_map.get(sid, None)

                raise RuntimeError('number of shells are inconsistent '
                                   '(%d != %d; %s) - %s' %
                                   (len(shell_ids), event.data.num_shells, 
                                    event.data.domain_id, diff))

        matrix_population = sum(len(container)
                                for container in self.containers)
        if shell_population != matrix_population:
            raise RuntimeError('num shells (%d) != matrix population (%d)' %
                               (shell_population, matrix_population))

    def check_domains(self):
        event_ids = set(domain.event_id
                        for domain in self.domains.itervalues())
        for id, event in self.scheduler:
            if id not in event_ids:
                raise RuntimeError('%s in EventScheduler not in self.domains' %
                                   event.data)
            event_ids.remove(id)

        # self.domains always include a None  --> this can change in future
        if event_ids:
            raise RuntimeError('following domains in self.domains not in '
                               'Event Scheduler: %s' % str(tuple(event_ids)))

    def check_pair_pos(self, pair, pos1, pos2, com, radius):
        particle1 = pair.single1.pid_particle_pair[1]
        particle2 = pair.single2.pid_particle_pair[1]

        old_com = com
        
        # debug: check if the new positions are valid:
        new_distance = self.world.distance(pos1, pos2)
        particle_radius12 = particle1.radius + particle2.radius

        # check 1: particles don't overlap.
        if new_distance <= particle_radius12:
            if __debug__:
                log.info('rejected move: radii %s, particle distance %s',
                         (FORMAT_DOUBLE % particle1.radius + particle2.radius,
                          FORMAT_DOUBLE % new_distance))
            if __debug__:
                log.debug('DEBUG: pair.dt %s, pos1 %s, pos2 %s' %
                          (FORMAT_DOUBLE % pair.dt, FORMAT_DOUBLE % pos1,
                           FORMAT_DOUBLE % pos2))
            raise RuntimeError('New particles overlap')

        # check 2: particles within mobility radius.
        d1 = self.world.distance(old_com, pos1) + particle1.radius
        d2 = self.world.distance(old_com, pos2) + particle2.radius
        if d1 > radius or d2 > radius:
            raise RuntimeError('New particle(s) out of protective sphere. ' 
                               'radius = %s, d1 = %s, d2 = %s ' %
                               (FORMAT_DOUBLE % radius, FORMAT_DOUBLE % d1,
                                FORMAT_DOUBLE % d2))

        return True




    def check(self):
        ParticleSimulatorBase.check(self)

        assert self.scheduler.check()

        assert self.t >= 0.0
        assert self.dt >= 0.0

        self.check_shell_matrix()
        self.check_domains()
        self.check_event_stoichiometry()
        
        self.check_obj_for_all()

    #
    # methods for debugging.
    #

    def dump_scheduler(self):
        """Dump scheduler information.

        """
        for id, event in self.scheduler:
            print id, event

    def dump(self):
        """Dump scheduler and event information.

        """
        for id, event in self.scheduler:
            print id, event, event.data

    def count_domains(self):
        # Returns a tuple (# Singles, # Pairs, # Multis).

        num_singles = 0
        num_pairs = 0
        num_multis = 0
        for d in self.domains.itervalues():
            if isinstance(d, Single):
                num_singles += 1
            elif isinstance(d, Pair):
                num_pairs += 1
            elif isinstance(d, Multi):
                num_multis += 1
            else:
                raise RuntimeError('DO NOT GET HERE')

        return (num_singles, num_pairs, num_multis)

    dispatch = [
        (Single, fire_single),
        (Pair, fire_pair),
        (Multi, fire_multi)
        ]


