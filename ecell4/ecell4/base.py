# coding: utf-8

from collections import OrderedDict

from ecell4.utils import *


APPLICATION='ecell4'


class Component(object):
    """Abstract base class for E-cell4 component.

    # setup
    >>> import os, tempfile
    >>> tfname = tempfile.mktemp()

    # frobnicate Component.
    >>> c = Component('foo')
    >>> c.name
    'foo'

    # saving
    >>> saved = c.save(tfname)
    >>> saved
    <HDF5 file "..." (mode ...)>
    >>> saved.attrs['application'], saved.attrs['format']
    ('ecell4', 'component')
    >>> saved.attrs['version']
    array([0, 0, 0])
    >>> sorted(saved)
    [u'metadata']
    >>> saved['metadata']
    <HDF5 group "/metadata" (0 members)>
    >>> list(saved['metadata'].attrs)
    [u'name']
    >>> saved['metadata'].attrs['name']
    'foo'
    >>> saved.close()

    # loading from nonexistent file will raise error.
    >>> c = Component('bar')
    >>> c.load('nonexistent')
    Traceback (most recent call last):
    ...
    IOError: File does not exist.

    # successfully load should restore props.
    >>> loaded = c.load(tfname)
    >>> loaded
    <HDF5 file "..." (mode r+)>
    >>> loaded.attrs['application'], loaded.attrs['format']
    ('ecell4', 'component')
    >>> loaded.attrs['version']
    array([0, 0, 0])
    >>> sorted(loaded)
    [u'metadata']
    >>> loaded['metadata']
    <HDF5 group "/metadata" (0 members)>
    >>> list(loaded['metadata'].attrs)
    [u'name']
    >>> loaded['metadata'].attrs['name']
    'foo'
    >>> loaded.close()

    # teardown
    >>> if os.path.exists(tfname): os.remove(tfname) # teardown
    
    """
    # (Persistency) version of this framework.
    VERSION = (0, 0, 0)
    # Versions of persistency this class supports.
    SUPPORTED_VERSIONS = [VERSION]

    def __init__(self, name=None):
        """
        Initializer.
        
        Attributes:
        name: Name of the component.
        
        """
        self.name = name

    def __repr__(self):
        return "<%s '%s'>" %(self.__class__.__name__, self.name)
    
    @property
    def typename(self):
        """Returns component type name.
        """
        return self.__class__.__name__.lower()
        
    @classmethod
    def Load(cls, hdf5_or_filename, strict_version=True):
        """Load instance from a file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.
        """
        instance = cls()
        instance.load(hdf5_or_filename, strict_version)
        return instance
            
    def load(self, hdf5_or_filename, strict_version=True):
        """Load data from a file (into exisiting instance).

        This method ALWAYS OVERWRITE instance attribute with loaded file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.

        This method *should return h5py.Group* on successful load, so that subclass
        can extend.

        """
        # find data
        data_root = find_hdf5(hdf5_or_filename, new=False)
        # validation 0: application, framework should be APPLICATION, self.typename.
        application = data_root.attrs.get('application', '(empty)')
        format_ = data_root.attrs.get('format', '(empty)')
        version = data_root.attrs.get('version', None)
        if not application==APPLICATION:
            raise FileError(
                "Attribute 'application' is %s, not %s." %(application, APPLICATION))
        if not format_==self.typename:
            raise FileError(
                "Attribute 'format' is %s, not %s." %(format_, self.typename))
        # validation #1: check version
        if strict_version:
            if version is None:
                raise FileError("Attribute 'version' not found.")
            tversion = tuple(version)
            if tversion not in self.SUPPORTED_VERSIONS:
                raise FileError(
                    "Attribute 'version' is %s, but supported versions are %s."
                    %(tversion, self.SUPPORTED_VERSIONS))
        # all green, ready to update. subclass should extend below.
        metadata_group = data_root.get('metadata', None)
        if metadata_group:
            self.name = metadata_group.attrs.get('name', None)
        # should return h5py.Group so that subclass can extend.
        return data_root

    def save(self, hdf5_or_filename, strict_version=True):
        """Save data into a file.

        This method ALWAYS OVERWRITE data in exisisting file.

        - hdf5_or_filename: h5py.File instance or string of file path.
        - strict_version: Raise error if file version is not in SUPPORTED VERSION.

        This method *should return h5py.Group* on successful load, so that subclass
        can extend.

        """
        # find data
        data_root = find_hdf5(hdf5_or_filename)
        # validation 0: application, framework should be APPLICATION, self.typename.
        application = data_root.attrs.get('application', None)
        format_ = data_root.attrs.get('format', None)
        version = data_root.attrs.get('version', None)
        if application is None:
            data_root.attrs['application'] = APPLICATION
        elif not application==APPLICATION:
            raise FileError(
                "Attribute 'application' is %s, not %s." %(application, APPLICATION))
        if format_ is None:
            format_ = self.typename
            data_root.attrs['format'] = format_
        if not format_==self.typename:
            raise FileError(
                "Attribute 'format' is %s, not %s." %(format_, self.typename))
        # validation #1: version
        if version is None:
            data_root.attrs['version'] = self.VERSION
        elif strict_version:
            tversion = tuple(version)
            if tversion not in self.SUPPORTED_VERSIONS:
                raise FileError(
                    "Attribute 'version' is %s, but supported versions are %s."
                    %(tversion, self.SUPPORTED_VERSIONS))
        # all green here, ready to serialize.
        metadata_group = data_root.get('metadata', None)
        if metadata_group is None:
            metadata_group = data_root.create_group('metadata')
        metadata_group.attrs['name'] = self.name
        # should return saved h5py.Group.
        return data_root


if __name__=='__main__':
    from doctest import testmod, ELLIPSIS
    testmod(optionflags=ELLIPSIS)
