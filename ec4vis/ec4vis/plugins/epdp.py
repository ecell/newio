# coding: utf-8

# PORTING DOT DONE YET, JUST A PLACEHOLDER STUFF.

"""
visualizer.py:

    Visialization module of particles and shells
     in HDF5 file outputed from E-Cell simulator

    Revision 0 (2010/1/25 released)
        First release of this module.
     
    Revision 1 (2010/2/26 released)
        New features:
            - Blurry effect of particles is available.
            - Exception class is added for visualizer.
        Bug fixes:
            - Fixed a bug caused that newly created Settings object has history
              of the old objects.

    This module uses following third-party libraries:
      - VTK (Visualization Tool Kit)
      - h5py (Python biding to HDF5 library)
      - numpy (Numerical Python)
      - FFmpeg (To make a movie from outputed snapshots)

    Please install above libraries before use this module.

"""

import os
import sys
import tempfile
import math
import time

import h5py
import vtk
import numpy

import domain_kind_constants
import rgb_colors
import default_settings
import copy


class VisualizerError(Exception):

    "Exception class for visualizer"

    def __init__(self, info):
        self.__info = info

    def __repr__(self):
        return self.__info

    def __str__(self):
        return self.__info


class Settings(object):

    "Visualization setting class for Visualizer"

    def __init__(self, user_settings_dict = None):

        settings_dict = default_settings.__dict__.copy()

        if user_settings_dict is not None:
            if type(user_settings_dict) != type({}):
                print 'Illegal argument type for constructor of Settings class'
                sys.exit()
            settings_dict.update(user_settings_dict)

        for key, val in settings_dict.items():
            if key[0] != '_': # Data skip for private variables in setting_dict.
                if type(val) == type({}) or type(val) == type([]):
                    copy_val = copy.deepcopy(val)
                else:
                    copy_val = val
                setattr(self, key, copy_val)

    def __set_data(self, key, val):
        if val != None:
            setattr(self, key, val)

    def set_image(self,
                  height = None,
                  width = None,
                  background_color = None,
                  file_name_format = None
                  ):

        self.__set_data('image_height', height)
        self.__set_data('image_width', width)
        self.__set_data('image_background_color', background_color)
        self.__set_data('image_file_name_format', file_name_format)

    def set_ffmpeg(self,
                   movie_file_name = None,
                   bin_path = None,
                   additional_options = None
                   ):
        self.__set_data('ffmpeg_movie_file_name', movie_file_name)
        self.__set_data('ffmpeg_bin_path', bin_path)
        self.__set_data('ffmpeg_additional_options', additional_options)

    def set_camera(self,
                   forcal_point = None,
                   base_position = None,
                   azimuth = None,
                   elevation = None,
                   view_angle = None
                   ):
        self.__set_data('camera_forcal_point', forcal_point)
        self.__set_data('camera_base_position', base_position)
        self.__set_data('camera_azimuth', azimuth)
        self.__set_data('camera_elevation', elevation)
        self.__set_data('camera_view_angle', view_angle)

    def set_light(self,
                  intensity = None
                  ):
        self.__set_data('light_intensity', intensity)

    def set_species_legend(self,
                           display = None,
                           border_display = None,
                           location = None,
                           height = None,
                           width = None,
                           offset = None
                           ):
        self.__set_data('species_legend_display', display)
        self.__set_data('species_legend_border_display', border_display)
        self.__set_data('species_legend_location', location)
        self.__set_data('species_legend_height', height)
        self.__set_data('species_legend_width', width)
        self.__set_data('species_legend_offset', offset)

    def set_time_legend(self,
                        display = None,
                        border_display = None,
                        format = None,
                        location = None,
                        height = None,
                        width = None,
                        offset = None
                        ):
        self.__set_data('time_legend_display', display)
        self.__set_data('time_legend_border_display', border_display)
        self.__set_data('time_legend_format', format)
        self.__set_data('time_legend_location', location)
        self.__set_data('time_legend_height', height)
        self.__set_data('time_legend_width', width)
        self.__set_data('time_legend_offset', offset)

    def set_wireframed_cube(self,
                            display = None
                            ):
        self.__set_data('wireframed_cube_diplay', display)

    def set_axis_annotation(self,
                            display = None,
                            color = None
                            ):
        self.__set_data('axis_annotation_display', display)
        self.__set_data('axis_annotation_color', color)

    def set_fluorimetry(self,
                         display = None,
                         axial_voxel_number = None,
                         background_color = None,
                         shadow_display = None,
                         accumulation_mode = None,
                         ):
        self.__set_data('fluorimetry_display', display)
        self.__set_data('fluorimetry_axial_voxel_number', axial_voxel_number)
        self.__set_data('fluorimetry_background_color', background_color)
        self.__set_data('fluorimetry_shadow_display', shadow_display)
        self.__set_data('fluorimetry_accumulation_mode', accumulation_mode)

    def add_plane_surface(self,
                         color = None,
                         opacity = None,
                         origin = None,
                         axis1 = None,
                         axis2 = None
                         ):

        color_ = self.plane_surface_color
        opacity_ = self.plane_surface_opacity
        origin_ = self.plane_surface_origin
        axis1_ = self.plane_surface_axis_1
        axis2_ = self.plane_surface_axis_2

        if color != None: color_ = color
        if opacity != None: opacity_ = opacity
        if origin != None: origin_ = origin
        if axis1 != None: axis1_ = axis1
        if axis2 != None: axis2_ = axis2

        self.plane_surface_list.append({'color':color_,
                                        'opacity':opacity_,
                                        'origin':origin_,
                                        'axis1':axis1_,
                                        'axis2':axis2_})

    def pfilter_func(self, particle, display_species_id, pattr):
        return pattr

    def pfilter_sid_map_func(self, species_id):
        return species_id

    def pfilter_sid_to_pattr_func(self, display_species_id):
        return self.particle_attrs.get(display_species_id,
                                       self.default_particle_attr)

    def dump(self):
        dump_list = []
        for key in self.__slots__:
            dump_list.append((key, getattr(self, key, None)))

        dump_list.sort(lambda a, b:cmp(a[0], b[0]))

        print '>>>>>>> Settings >>>>>>>'
        for x in dump_list:
            print x[0], ':', x[1]
        print '<<<<<<<<<<<<<<<<<<<<<<<<'


class Renderer(object):
    def __init__(self, settings, species_list, world_size):
        assert  isinstance(settings, Settings)
        assert world_size is not None
        self.settings = settings
        self.__world_size = world_size

        self.__build_particle_attrs(species_list)
        self.__build_domain_attrs()
        self.renderer = self.__create_renderer()

        self.__axes = None
        self.__cube = None
        self.__species_legend = None
        self.__time_legend = None
        self.__plane_list = self.__create_planes()

        # Create axis annotation
        if self.settings.axis_annotation_display:
            self.__axes = self.__create_axes()
            self.__axes.SetCamera(self.renderer.GetActiveCamera())

        # Create a wireframed cube
        if self.settings.wireframed_cube_display:
            self.__cube = self.__create_wireframe_cube()

        # Create species legend box
        if self.settings.species_legend_display:
            self.__species_legend = self.__create_species_legend()

        # Create time legend box
        if self.settings.time_legend_display:
            self.__time_legend = self.__create_time_legend()

    def __get_domain_color(self, domain_kind):
        return self.__dattrs.get \
                (domain_kind, self.settings.default_domain_attr)['color']

    def __get_domain_opacity(self, domain_kind):
        return self.__dattrs.get \
                (domain_kind, self.settings.default_domain_attr)['opacity']

    def __get_legend_position(self, location, height, width, offset):
        if location == 0:
            return (offset, offset)
        elif location == 1:
            return (1.0 - width - offset, offset)
        elif location == 2:
            return (offset, 1.0 - height - offset)
        elif location == 3:
            return (1.0 - width - offset, 1.0 - height - offset)
        else:
            raise VisualizerError('Illegal legend position: %d' % location)

    def __create_planes(self):
        plane_list = []
        scaling = self.settings.scaling
        for x in self.settings.plane_surface_list:
            actor = vtk.vtkActor()
            plane = vtk.vtkPlaneSource()
            plane.SetOrigin(x['origin'] * scaling)
            plane.SetPoint1(x['axis1'] * scaling)
            plane.SetPoint2(x['axis2'] * scaling)

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInput(plane.GetOutput())

            actor.SetMapper(mapper)
            prop = actor.GetProperty()
            prop.SetColor(x['color'])
            prop.SetOpacity(x['opacity'])
            plane_list.append(actor)

        return plane_list

    def __build_particle_attrs(self, species_list):
        # Data transfer of species dataset to the dictionary
        species_dict = {}
        species_idmap = {}
        for species in species_list:
            species_id = species['id']
            display_species_id = self.settings.pfilter_sid_map_func(species_id)
            if display_species_id is not None:
                species_idmap[species_id] = display_species_id
                species_dict[species_id] = dict((species.dtype.names[i], v) for i, v in enumerate(species))

        # Delete duplicated numbers by set constructor
        self.__species_idmap = species_idmap
        self.__reverse_species_idmap = dict((v, k) for k, v in species_idmap.iteritems())

        # Set particle attributes
        self.__pattrs = {}
        nondisplay_species_idset = set()

        for species_id, display_species_id in self.__reverse_species_idmap.iteritems():
            # Get default color and opacity from default_settings
            _def_attr = self.settings.pfilter_sid_to_pattr_func(display_species_id)
            if _def_attr is not None:
                def_attr = dict(_def_attr)
                def_attr.update(species_dict[species_id])
                self.__pattrs[display_species_id] = def_attr

        self.__mapped_species_idset = self.__pattrs.keys()

    def __build_domain_attrs(self):
        self.__dattrs = self.settings.domain_attrs

    def __create_camera(self):
        # Create a camera
        camera = vtk.vtkCamera()

        camera.SetFocalPoint(
            numpy.array(self.settings.camera_focal_point) *
            self.settings.scaling)
        camera.SetPosition(numpy.array(self.settings.camera_base_position) *
            self.settings.scaling)

        camera.Azimuth(self.settings.camera_azimuth)
        camera.Elevation(self.settings.camera_elevation)
        camera.SetViewAngle(self.settings.camera_view_angle)
        return camera

    def __add_lights_to_renderer(self, renderer):
        # Create a automatic light kit
        light_kit = vtk.vtkLightKit()
        light_kit.SetKeyLightIntensity(self.settings.light_intensity)
        light_kit.AddLightsToRenderer(renderer)

    def __create_renderer(self):
        renderer = vtk.vtkRenderer()
        renderer.SetViewport(0.0, 0.0, 1., 1.)
        renderer.SetActiveCamera(self.__create_camera())
        renderer.SetBackground(self.settings.image_background_color)
        self.__add_lights_to_renderer(renderer)
        return renderer

    def __create_axes(self):
        axes = vtk.vtkCubeAxesActor2D()
        axes.SetBounds(numpy.array([0.0, 1.0, 0.0, 1.0, 0.0, 1.0]) * self.settings.scaling)
        axes.SetRanges(0.0, self.__world_size,
                              0.0, self.__world_size,
                              0.0, self.__world_size)
        axes.SetLabelFormat('%g')
        axes.SetFontFactor(1.5)
        tprop = vtk.vtkTextProperty()
        tprop.SetColor(self.settings.axis_annotation_color)
        tprop.ShadowOn()
        axes.SetAxisTitleTextProperty(tprop)
        axes.SetAxisLabelTextProperty(tprop)
        axes.UseRangesOn()
        axes.SetCornerOffset(0.0)

        return axes

    def __create_wireframe_cube(self):
        cube = vtk.vtkCubeSource()
        scaling = self.settings.scaling
        cube.SetBounds(numpy.array([0.0, 1.0, 0.0, 1.0, 0.0, 1.0]) * scaling)
        cube.SetCenter(numpy.array([0.5, 0.5, 0.5]) * scaling)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(cube.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetRepresentationToWireframe()
        return actor

    def __create_time_legend(self):
        time_legend = vtk.vtkLegendBoxActor()

        # Create legend actor
        time_legend.SetNumberOfEntries(1)
        time_legend.SetPosition(
            self.__get_legend_position(
                self.settings.time_legend_location,
                self.settings.time_legend_height,
                self.settings.time_legend_width,
                self.settings.time_legend_offset))

        time_legend.SetWidth(self.settings.time_legend_width)
        time_legend.SetHeight(self.settings.time_legend_height)

        tprop = vtk.vtkTextProperty()
        tprop.SetColor(rgb_colors.RGB_WHITE)
        tprop.SetVerticalJustificationToCentered()
        time_legend.SetEntryTextProperty(tprop)

        if self.settings.time_legend_border_display:
            time_legend.BorderOn()
        else:
            time_legend.BorderOff()
        return time_legend

    def __create_species_legend(self):
        species_legend = vtk.vtkLegendBoxActor()
        # Get number of lines
        legend_line_numbers = len(self.__mapped_species_idset) \
                            + len(domain_kind_constants.DOMAIN_KIND_NAME)

        # Create legend actor
        species_legend.SetNumberOfEntries(legend_line_numbers)
        species_legend.SetPosition(
            self.__get_legend_position(
                self.settings.species_legend_location,
                self.settings.species_legend_height,
                self.settings.species_legend_width,
                self.settings.species_legend_offset))
        species_legend.SetWidth(self.settings.species_legend_width)
        species_legend.SetHeight(self.settings.species_legend_height)

        tprop = vtk.vtkTextProperty()
        tprop.SetColor(rgb_colors.RGB_WHITE)
        tprop.SetVerticalJustificationToCentered()

        species_legend.SetEntryTextProperty(tprop)

        if self.settings.species_legend_border_display:
            species_legend.BorderOn()
        else:
            species_legend.BorderOff()

        # Entry legend string to the actor
        sphere = vtk.vtkSphereSource()

        # Create legends of particle speices
        count = 0
        for species_id in self.__mapped_species_idset:
            species_legend.SetEntryColor \
                (count, self.__pattrs[species_id]['color'])
            species_legend.SetEntryString \
                (count, self.__pattrs[species_id]['name'])
            species_legend.SetEntrySymbol(count, sphere.GetOutput())
            count += 1

        # Create legends of shell spesies
        offset = count
        count = 0
        for kind, name in domain_kind_constants.DOMAIN_KIND_NAME.items():
            species_legend.SetEntryColor \
                (offset + count, self.__get_domain_color(kind))
            species_legend.SetEntrySymbol \
                (offset + count, sphere.GetOutput())
            species_legend.SetEntryString(offset + count, name)
            count += 1
        return species_legend

    def __render_particles(self, particles_dataset):
        # Data transfer from HDF5 dataset to numpy array for fast access
        scaling = self.settings.scaling
        species_id_idx = particles_dataset.dtype.names.index('species_id')
        position_idx = particles_dataset.dtype.names.index('position')

        for x in particles_dataset:
            display_species_id = self.__species_idmap.get(x[species_id_idx])
            if display_species_id is None:
                continue
            pattr = self.__pattrs.get(display_species_id)
            if pattr is None:
                continue
            pattr = self.settings.pfilter_func(x, display_species_id, pattr)
            if pattr is not None:
                sphere = vtk.vtkSphereSource()
                sphere.SetRadius(scaling * pattr['radius'] / self.__world_size)
                sphere.SetCenter(scaling * x[position_idx] / self.__world_size)

                mapper = vtk.vtkPolyDataMapper()
                mapper.SetInput(sphere.GetOutput())

                sphere_actor = vtk.vtkActor()
                sphere_actor.SetMapper(mapper)
                sphere_actor.GetProperty().SetColor(pattr['color'])
                sphere_actor.GetProperty().SetOpacity(pattr['opacity'])

                self.renderer.AddActor(sphere_actor)

    def __render_blurry_particles(self, particles_dataset):
        particles_per_species = dict((k, vtk.vtkPoints()) for k in self.__species_idmap.iterkeys())

        scaling = self.settings.scaling

        position_idx = particles_dataset.dtype.names.index('position')
        species_id_idx = particles_dataset.dtype.names.index('species_id')
        for p in particles_dataset:
            pos = p[position_idx]
            display_species_id = self.__species_idmap.get(p[species_id_idx])
            if display_species_id is None:
                continue
            particles_per_species[display_species_id].InsertNextPoint(
                pos * scaling / self.__world_size)

        nx = ny = nz = self.settings.fluorimetry_axial_voxel_number

        for display_species_id, points in particles_per_species.iteritems():
            poly_data = vtk.vtkPolyData()
            poly_data.SetPoints(points)
            poly_data.ComputeBounds()

            pattr = self.__pattrs[display_species_id]
            # Calc standard deviation of gauss distribution function
            wave_length = pattr['fluorimetry_wave_length']
            sigma = scaling * 0.5 * wave_length / self.__world_size

            # Create guassian splatter
            gs = vtk.vtkGaussianSplatter()
            gs.SetInput(poly_data)
            gs.SetSampleDimensions(nx, ny, nz)
            gs.SetRadius(sigma)
            gs.SetExponentFactor(-.5)
            gs.ScalarWarpingOff()
            gs.SetModelBounds([-sigma, scaling + sigma] * 3)
            gs.SetAccumulationModeToMax()

            # Create filter for volume rendering
            filter = vtk.vtkImageShiftScale()
            # Scales to unsigned char
            filter.SetScale(255. * pattr['fluorimetry_brightness'])
            filter.ClampOverflowOn()
            filter.SetOutputScalarTypeToUnsignedChar()
            filter.SetInputConnection(gs.GetOutputPort())

            mapper = vtk.vtkFixedPointVolumeRayCastMapper()
            mapper.SetInputConnection(filter.GetOutputPort())

            volume = vtk.vtkVolume()
            property = volume.GetProperty() # vtk.vtkVolumeProperty()
            color = pattr['fluorimetry_luminescence_color']
            color_tfunc = vtk.vtkColorTransferFunction()
            color_tfunc.AddRGBPoint(0, color[0], color[1], color[2])
            property.SetColor(color_tfunc)
            opacity_tfunc = vtk.vtkPiecewiseFunction()
            opacity_tfunc.AddPoint(0, 0.0)
            opacity_tfunc.AddPoint(255., 1.0)
            property.SetScalarOpacity(opacity_tfunc)
            property.SetInterpolationTypeToLinear()

            if self.settings.fluorimetry_shadow_display:
                property.ShadeOn()
            else:
                property.ShadeOff()

            volume.SetMapper(mapper)

            self.renderer.AddVolume(volume)

    def __render_shells(self,
                        shells_dataset,
                        domain_shell_assoc,
                        domains_dataset):

        # Data transfer from HDF5 dataset to numpy array for fast access
        shells_array = numpy.zeros(shape = shells_dataset.shape,
                                   dtype = shells_dataset.dtype)

        shells_dataset.read_direct(shells_array)

        # Construct assosiaction dictionary
        domain_shell_assoc_array = numpy.zeros(shape = domain_shell_assoc.shape,
                                               dtype = domain_shell_assoc.dtype)

        domain_shell_assoc.read_direct(domain_shell_assoc_array)
        domain_shell_assoc_dict = dict(domain_shell_assoc_array)

        # Construct domains dictionary
        domains_array = numpy.zeros(shape = domains_dataset.shape,
                                    dtype = domains_dataset.dtype)

        domains_dataset.read_direct(domains_array)
        domains_dict = dict(domains_array)

        # Add shell actors
        for x in shells_array:

            shell_id = x['id']

            try:
                domain_id = domain_shell_assoc_dict[shell_id]
            except KeyError:
                raise VisualizerError \
                    ('Illegal shell_id is found in dataset of domain_shell_association!')

            try:
                domain_kind = domains_dict[domain_id]
            except KeyError:
                raise VisualizerError \
                    ('Illegal domain_id is found in domains dataset!')

            if self.__get_domain_opacity(domain_kind) > 0.0:

                sphere = vtk.vtkSphereSource()
                sphere.SetRadius(x['radius'] / self.__world_size)
                sphere.SetCenter(x['position'][0] / self.__world_size,
                                 x['position'][1] / self.__world_size,
                                 x['position'][2] / self.__world_size)

                mapper = vtk.vtkPolyDataMapper()
                mapper.SetInput(sphere.GetOutput())

                sphere_actor = vtk.vtkActor()
                sphere_actor.SetMapper(mapper)
                sphere_actor.GetProperty().SetColor \
                    (self.__get_domain_color(domain_kind))
                sphere_actor.GetProperty().SetRepresentationToWireframe()
                sphere_actor.GetProperty().SetOpacity \
                    (self.__get_domain_opacity(domain_kind))

                self.renderer.AddActor(sphere_actor)

    def __reset_actors(self):
        self.renderer.RemoveAllViewProps()

        if self.__axes is not None:
            self.renderer.AddViewProp(self.__axes)

        if self.__cube is not None:
            self.renderer.AddActor(self.__cube)

        if self.__species_legend is not None:
            self.renderer.AddActor(self.__species_legend)

        if self.__time_legend is not None:
            self.renderer.AddActor(self.__time_legend)

        for plane in self.__plane_list:
            self.renderer.AddActor(plane)

    def render(self, t, particles_dataset, shells_dataset=None,
               domain_shell_assoc=None, domains_dataset=None):
        self.__reset_actors()
        if self.__time_legend is not None:
            self.__time_legend.SetEntryString(0,
                self.settings.time_legend_format % t)

        if self.settings.fluorimetry_display:
            self.__render_blurry_particles(particles_dataset)
        else:
            if self.settings.render_particles:
                self.__render_particles(particles_dataset)

            if self.settings.render_shells and shells_dataset is not None:
                self.__render_shells(shells_dataset,
                                     domain_shell_assoc,
                                     domains_dataset)


class Visualizer(object):
    "Visualization class of e-cell simulator"

    def __init__(self, hdf5_file_path_list, image_file_dir=None, movie_filename='movie.mp4', cleanup_image_file_dir=False, settings=Settings()):
        assert isinstance(settings, Settings)

        self.settings = settings

        if image_file_dir is None:
            image_file_dir = tempfile.mkdtemp(dir=os.getcwd())
            cleanup_image_file_dir = True

        self.image_file_dir = image_file_dir
        self.__cleanup_image_file_dir = cleanup_image_file_dir
        self.__movie_filename = movie_filename

        particles_time_sequence = []
        shells_time_sequence = []
        world_size = None
        species_list = None

        for hdf5_file_path in hdf5_file_path_list:
            try:
                hdf5_file = h5py.File(hdf5_file_path, 'r')
                data_group = hdf5_file['data']
                species_dataset = hdf5_file['species']
                if species_dataset is not None:
                    species_list = numpy.zeros(shape=species_dataset.shape,
                                               dtype=species_dataset.dtype)
                    species_dataset.read_direct(species_list)

                _world_size = data_group.attrs['world_size']
                if world_size is not None and _world_size != world_size:
                    raise VisualizerError('World sizes differ between datagroups')
                world_size = _world_size

                for time_group_name in data_group:
                    time_group = data_group[time_group_name]
                    elem = (time_group.attrs['t'], hdf5_file_path, time_group_name)
                    if 'particles' in time_group.keys():
                        particles_time_sequence.append(elem)
                    if 'shells' in time_group.keys():
                        shells_time_sequence.append(elem)

                hdf5_file.close()
            except Exception, e:
                if not self.settings.ignore_open_errors:
                    raise
                print 'Ignoring error: ', e

        if species_list is None:
            raise VisualizerError(
                    'Cannot find species dataset in any given hdf5 files')

        if len(particles_time_sequence) == 0:
            raise VisualizerError(
                    'Cannot find particles dataset in any given hdf5 files: ' \
                    + ', '.join(hdf5_file_path_list))

        if world_size is None:
            raise VisualizerError(
                    'Cannot determine world_size from given hdf5 files: ' \
                    + ', '.join(hdf5_file_path_list))

        # Sort ascending time order
        particles_time_sequence.sort(lambda a, b:cmp(a[0], b[0]))
        # Sort descending time order
        shells_time_sequence.sort(lambda a, b:cmp(a[0], b[0]))

        idx = 0
        time_sequence = []
        for pentry in particles_time_sequence:
            while idx < len(shells_time_sequence) and shells_time_sequence[idx][0] <= pentry[0]:
                idx += 1
            idx -= 1
            if idx < 0:
                idx = 0
                sentry = (None, None, None)
            else:
                sentry = shells_time_sequence[idx]
            time_sequence.append(
                (pentry[0], pentry[1], pentry[2], sentry[1], sentry[2]))
        
        self.__world_size = world_size
        self.time_sequence = time_sequence

        self.__renderer = Renderer(self.settings, species_list, world_size)
        window = vtk.vtkRenderWindow()
        window.SetSize(int(self.settings.image_width),
                       int(self.settings.image_height))
        window.SetOffScreenRendering(self.settings.offscreen_rendering)
        window.AddRenderer(self.__renderer.renderer)
        self.window = window

    def __del__(self):
        if self.__cleanup_image_file_dir:
            for parent_dir, dirs, files in os.walk(self.image_file_dir, False):
                for file in files:
                    os.remove(os.path.join(parent_dir, file))
                os.rmdir(parent_dir)

    def save_rendered(self, image_file_name):
        "Output snapshot to image file"

        image_file_type = os.path.splitext(image_file_name)[1]

        # Remove existing image file
        if os.path.exists(image_file_name):
            if os.path.isfile(image_file_name):
                os.remove(image_file_name)
            else:
                raise VisualizerError \
                    ('Cannot overwrite image file: ' + image_file_name)

        if image_file_type == '.bmp':
            writer = vtk.vtkBMPWriter()
        elif image_file_type == '.jpg':
            writer = vtk.vtkJPEGWriter()
        elif image_file_type == '.png':
            writer = vtk.vtkPNGWriter()
        elif image_file_type == '.tif':
            writer = vtk.vtkTIFFWriter()
        else:
            error_info = 'Illegal image-file type: ' + image_file_type + '\n'
            error_info += 'Please choose from "bmp","jpg","png","tif".'
            raise VisualizerError(error_info)

        w2i = vtk.vtkWindowToImageFilter()
        w2i.SetInput(self.window)
        self.window.Render()

        writer.SetInput(w2i.GetOutput())
        writer.SetFileName(image_file_name)
        writer.Write()

    def output_snapshots(self):
        "Output snapshots from HDF5 dataset"

        # Create image file folder
        if not os.path.exists(self.image_file_dir):
            os.makedirs(self.image_file_dir)

        time_count = 0
        snapshot_file_list = []

        for entry in self.time_sequence:
            image_file_name = \
                os.path.join(self.image_file_dir,
                             self.settings.image_file_name_format % time_count)
            self.render(*entry[1:])
            self.save_rendered(image_file_name)
            snapshot_file_list.append(image_file_name)
            time_count += 1

        return snapshot_file_list

    def render(self, hdf5_file_name, time_group_name, shells_hdf5_file_name,
               shells_time_group_name):
        hdf5_file = h5py.File(hdf5_file_name, 'r')
        shells_hdf5_file = None
        if shells_hdf5_file_name is not None:
            if shells_hdf5_file_name != hdf5_file_name:
                shells_hdf5_file = h5py.File(shells_hdf5_file_name, 'r')
            else:
                shells_hdf5_file = hdf5_file

        try:
            data_group = hdf5_file['data']
            species_dataset = hdf5_file['species']

            world_size = data_group.attrs['world_size']
            time_group = data_group[time_group_name]
            t = time_group.attrs['t'] 

            shells_dataset = None
            domain_shell_assoc = None
            domains_dataset = None

            if shells_hdf5_file is not None:
                shells_time_group = shells_hdf5_file['data'][shells_time_group_name]
                shells_dataset = shells_time_group['shells']
                domain_shell_assoc = shells_time_group['domain_shell_association']
                domains_dataset = shells_time_group['domains']

            self.__renderer.render(t, time_group['particles'],
                    shells_dataset, domain_shell_assoc, domains_dataset)

        finally:
            if shells_hdf5_file is not None and \
               shells_hdf5_file is not hdf5_file:
                shells_hdf5_file.close()

            hdf5_file.close()

    def make_movie(self):
        """
        Make a movie by FFmpeg
        Please install FFmpeg (http://ffmpeg.org/) from the download site
         before use this function.
        """

        input_image_filename = \
            os.path.join(self.image_file_dir,
                         self.settings.image_file_name_format)

        # Set FFMPEG options
        options = self.settings.ffmpeg_additional_options \
            + ' -y -i "' + input_image_filename + '" ' \
            + self.__movie_filename

        os.system(self.settings.ffmpeg_bin_path + ' ' + options)

    def output_movie(self):
        """
        Output movie to movie_file_dir
        This function creates temporal image files to output the movie.
        These temporal files and directory are removed after the output.
        """
        self.output_snapshots()
        self.make_movie()


class InteractingVisualizer(Visualizer):
    def __init__(self, *arg, **kwarg):
        Visualizer.__init__(self, *arg, **kwarg)
        self.interactor = self.window.MakeRenderWindowInteractor()
        self.interactor.SetRenderWindow(self.window)
        self.interactor.Initialize()
        self.time_count = 0
        self.timer_id = None

    def __timer_callback(self, obj, event_id):
        if self.time_count < len(self.time_sequence):
            entry = self.time_sequence[self.time_count]
            image_file_name = \
                os.path.join(self.image_file_dir,
                             self.settings.image_file_name_format % self.time_count)
            self.render(*entry[1:])
            self.save_rendered(image_file_name)
            self.time_count += 1
        else:
            self.interactor.DestroyTimer(self.timer_id)

    def output_snapshots(self):
        "Output snapshots from HDF5 dataset"

        # Create image file folder
        if not os.path.exists(self.image_file_dir):
            os.makedirs(self.image_file_dir)

        self.time_count = 0

        self.timer_id = self.interactor.CreateRepeatingTimer(1000)
        self.interactor.AddObserver('TimerEvent', self.__timer_callback, .0)
        self.interactor.Start()

