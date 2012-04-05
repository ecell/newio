# coding: utf-8
"""Random file-related utilities.
"""
import os
from h5py import File, Group


class FileError(IOError):
    """Error raised on file-related errors."""
    pass


def find_hdf5(bits, mode=None, new=True, **kwargs):
    """
    Force bits to h5py.File object.

    Argument bits can accept both string or h5py.Group object.
    If bits is a string, it is treated as path to a file.
    'mode' argument specifies file mode if bits is string.
    If 'new' is set to True, or specified path already exists,
    h5py.File is opened and returned. If new is set to False
    and file does not exists, IOError is raised.
    Any bits not either string nor h5py.Group will raise TypeError.
    Any optional arguments
    
    # setup
    >>> import os, tempfile
    >>> tfname1 = tempfile.mktemp()
    >>> tfname2 = tempfile.mktemp()
    >>> tfname3 = tempfile.mktemp()
    >>> tfname4 = tempfile.mktemp()

    # find by path
    >>> f = File(tfname1)

    # find by h5py.Group results itself.
    >>> find_hdf5(f)==f
    True

    # file creation defaults to readwrite empty file.
    >>> find_hdf5(tfname2)
    <HDF5 file "..." (mode r+)>

    # mode 'w' implies r+. # this may differ on other platform...
    >>> find_hdf5(tfname3, mode='w')
    <HDF5 file "..." (mode r+)>

    # new=False and nonexistent path will raise error.
    >>> find_hdf5(tfname4, new=False)
    Traceback (most recent call last):
    ...
    IOError: File does not exist.

    # teardown
    >>> if os.path.exists(tfname1): os.remove(tfname1)
    >>> if os.path.exists(tfname2): os.remove(tfname2)
    >>> if os.path.exists(tfname3): os.remove(tfname3)
    >>> if os.path.exists(tfname4): os.remove(tfname4)
    
    
    """
    if isinstance(bits, Group): # implies File, as a subclass.
        return bits
    elif isinstance(bits, (str, unicode)):
        if new==True or os.path.isfile(bits):
            return File(bits, mode=mode, **kwargs)
        raise IOError('File does not exist.')
    else:
        raise TypeError('Invalid argument: h5py.File or string are allowed.')


def load_component(data_group, registry=tuple(), strict_version=True):
    """Load component from data_group with Component class defined in registry.

    data_group should have 'type' attribute which should in turn defined in
    registry. Registry is a sequence of tuples, each containing
    ('type_string', ComponentClass).

    # setup
    >>> import os, tempfile
    >>> from base import Component
    >>> tfname = tempfile.mktemp()
    >>> data_root = find_hdf5(tfname, new=True)
    >>> c1 = Component(name='foo')
    >>> registry=(('component-foo', Component),)

    # save with registry.
    >>> save_component(data_root, c1, registry)
    <HDF5 file "..." (mode r+)>

    # load without registry will raise error.
    >>> data_root = find_hdf5(tfname, new=True)
    >>> load_component(data_root)
    Traceback (most recent call last):
    ...
    ValueError: Registry does not have appropreate entry for type 'component-foo'.

    # verify
    >>> c1 = load_component(data_root, registry)
    >>> c1, vars(c1).items()
    (<Component 'foo'>, [('name', 'foo')])

    # teardown
    >>> if os.path.exists(tfname): os.remove(tfname)

    """
    type_to_class = dict(registry)
    type_string = data_group.attrs.get('type', None)
    if type_string is None:
        raise ValueError(
            "'type' attribute is not defined in the data.")
    ComponentClass = type_to_class.get(type_string, None)
    if ComponentClass is None:
        raise ValueError(
            "Registry does not have appropreate entry for type '%s'."
            %(type_string))
    return ComponentClass.Load(data_group, strict_version)


def save_component(data_group, component, registry=tuple(), strict_version=True):
    """Save component into a data group, with type attribute defined in registry.

    Component should have 'type' attribute which should in turn defined in
    registry. Registry is a sequence of tuples, each containing
    ('type_string', ComponentClass).

    # setup
    >>> import os, tempfile
    >>> from base import Component
    >>> tfname = tempfile.mktemp()
    >>> data_root = find_hdf5(tfname, new=True)
    >>> c1 = Component(name='foo')

    # will raise error
    >>> save_component(data_root, c1)
    Traceback (most recent call last):
    ...
    ValueError: Type-string is not defined for class: Component.

    >>> registry=(('component-foo', Component),)
    >>> save_component(data_root, c1, registry)
    <HDF5 file "..." (mode r+)>

    # verify
    >>> data_root = find_hdf5(tfname, new=False)
    >>> list(data_root), data_root.attrs.items()
    ([u'metadata'], [(u'application', 'ecell4'), (u'format', 'component'), (u'version', array([0, 0, 0])), (u'type', 'component-foo')])
    >>> data_root
    <HDF5 file "..." (mode r+)>

    # teardown
    >>> if os.path.exists(tfname): os.remove(tfname)

    """
    class_to_type = dict((v, k) for k, v in list(registry))
    component_class = component.__class__
    component_type = class_to_type.get(component_class, None)
    if component_type is None:
        raise ValueError("Type-string is not defined for class: %s."
            %(component_class.__name__))
    component.save(data_group, strict_version)
    # overwrite component type
    data_group.attrs['type']= component_type
    return data_group
    

def save_named_component(parent_data_group, name, component, registry=tuple(), strict_version=True):
    """Save component into a data group under the parent_data_group,
    with type attribute defined in registry.

    Component should have 'type' attribute which should in turn defined in
    registry. Registry is a sequence of tuples, each containing
    ('type_string', ComponentClass).

    # setup
    >>> import os, tempfile
    >>> from base import Component
    >>> tfname = tempfile.mktemp()
    >>> data_root = find_hdf5(tfname, new=True)
    >>> c1 = Component(name='foo')

    # will raise error
    >>> save_named_component(data_root, 'foo_under_root', c1)
    Traceback (most recent call last):
    ...
    ValueError: Type-string is not defined for class: Component.

    >>> registry=(('component-foo', Component),)
    >>> save_named_component(data_root, 'foo_under_root', c1, registry)
    <HDF5 group "/foo_under_root" (1 members)>

    # verify
    >>> data_root = find_hdf5(tfname, new=False)
    >>> list(data_root), data_root.attrs.items()
    ([u'foo_under_root'], [])
    >>> foo = data_root['foo_under_root']
    >>> foo
    <HDF5 group "/foo_under_root" (1 members)>
    >>> list(foo), foo.attrs.items()
    ([u'metadata'], [(u'application', 'ecell4'), (u'format', 'component'), (u'version', array([0, 0, 0])), (u'type', 'component-foo')])

    # teardown
    >>> if os.path.exists(tfname): os.remove(tfname)
    
    """
    group_to_save = parent_data_group.get(name, None)
    if group_to_save is None:
        # if not exist, prepare the one.
        group_to_save = parent_data_group.create_group(name)
    return save_component(group_to_save, component, registry, strict_version)

    

if __name__=='__main__':
    from doctest import testmod, ELLIPSIS
    testmod(optionflags=ELLIPSIS)
