import maya.cmds as cmds
from maya.api.OpenMaya import MVector, MMatrix
import itertools
import numbers

"""
nodule.py

Pythonic property access for maya objects.

(C) 2018 Steve Thedoore
"""


def nodule(obj, typed=True):
    """
    Get the appropriate nodule for <obj>. 

    If 'typed' flag is set to true (the default), the nodule will be based on the
    node type of <obj>.  However, this only works if <obj> is a valid Maya object;
    if the supplied object doesn't exist when this function is called with 'typed'
    the function will raise a NoMayaObjectError.  If typed is false _and_ the
    object does not exist, the function will return a generic NodeProxy.
    """

    try:
        obj, nodetype = cmds.ls(obj, showType=True)
    except ValueError:
        if typed:
            raise NoMayaObjectError("object '{}' does not exist".format(obj))
        else:
            return Nodule(obj)

    wrapper = SPECIALTIES.get(nodetype)
    if not wrapper:
        wrapper = type(str(nodetype + "Nodule"), (Nodule,), {"LOOKUPS": {}})
        register_nodule_class(nodetype, wrapper)

    return wrapper(obj)


def nodule_from_uuid(uuid):
    """
    Return a nodule for the supplied UUID.  Raises a NoMayaObjectError if the UUID
    is invalid
    """
    target = cmds.ls(uuid)
    if target:
        return nodule(target[0])
    else:
        raise NoMayaObjectError("object '{}' does not exist".format(uuid))


def nodules_from_list(iterable):
    """
    Yields nodules for a list of objects.  This is faster than doing
    a series of one-at-a-time calls to nodule()
    """
    objects_and_types = cmds.ls(*iterable, showType=True)
    objects = itertools.islice(objects_and_types, 0, None, 2)
    nodetypes = itertools.islice(objects_and_types, 1, None, 2)
    for each_obj, each_type in itertools.izip(objects, nodetypes):
        wrapper = SPECIALTIES.get(each_type, Nodule)
        yield wrapper(each_obj)


def rename(original, new_name):
    """
    renames <original> to <new_name> and returns a proxy for the result
    """
    renamed = cmds.rename(original, new_name)
    return nodule(renamed)


def address_of(item):
    """
    Given an attribute access, return the string address of that attribute:

         test = proxy('pCube1')
         address_of(test.tx)

         >> 'pCube1.tx'

    if <item> is a string, it's returned unchanged.returned

    This function is primarily useful for mixing more elaborate forms of attribute
    management using cmds.setAttr that aren't supported by proxies:

        attribute = address_of(test.some_attribute)
        cmds.setAttr(attribute, indexMatters=False)

    """
    if hasattr(item, '_attribute'):
        return item._attribute
    else:
        return str(item)


def connect(a, b, force=False):
    """
    Connects the first atribute to the second.  Either argument
    can be a string or the result of a proxy property :

        connect ( proxy1.tx,  proxy2.ty)
        connect ( proxy1.tx,  "someobject.ty")
        connect ( "someobject.ty", proxy2.rx)
    """
    return cmds.connectAttr(address_of(a), address_of(b), force=force)


def disconnect(a, b):
    """
    Dionnects the first atribute from the second.  Either argument
    can be a string or the result of a proxy property :

        disconnect ( proxy1.tx,  proxy2.ty)
        disconnect ( proxy1.tx,  "someobject.ty")
        disconnect ( "someobject.ty", proxy2.rx)
    """
    return cmds.disconnectAttr(address_of(a), address_of(b))


def inputs_of(attr):
    """
    returns a tuple of proxies for any objects feeding in to attribute <attr>.  Argument
    can be a proxy property or a string:

        inputs_of (proxy1.tx)
        inputs_of ("someobject.ty")
    """
    return tuple(nodules_from_list(cmds.listConnections(address_of(attr), s=True, d=False, scn=True)))


def outputs_of(attr):
    """
    Returns a tuple of proxies for any objects connected to attribute <attr>.  Argument
    can be a proxy property or a string:

        outputs_of (proxy1.tx)
        outputs_of ("someobject.ty")
    """
    return tuple(nodules_from_list(cmds.listConnections(address_of(attr), d=True, s=False, scn=True)))


def register_nodule_class(type_string, proxy_class):
    """
    Registers a new subtype of Nodule for a given maya node type string.
    For example, if you want to register a dedicated proxy type for cameras,
    you would subclass Nodule:

        class CameraProxy(Nodule)):

            focalLength = make_descriptor('focalLength', 'double')
            fStop = make_descriptor('fStop', 'float')
            motionBlurOverride = make_descriptor('motionBlurOverride', 'enum')
            ... etc

    and then register it:

        register_nodule_class('camera', CameraProxy )

    the nodule(), nodule_from_uuid() and nodules_from_list() will now return the custom
    node type for cameras.
    """
    SPECIALTIES[type_string] = proxy_class


# -------------- module internals below here ------------------

class Connectable(object):
    """
    This is a mixin class which is added to values coming back from a property
    access to let them do double-duty as both regular values (numbers, vectors, etc)
    and also as targets or sources for connections and expressions like

        something.property.locked = True

    """

    def connect(self, other):
        """ = cmds.connectAttr( self._attribute, other._attribute ) """
        connect(self, other)

    def disconnect(self, other):
        """ = cmds.disconnectAttr( self._attribute, other._attribute ) """
        disconnect(self, other)

    def inputs(self):
        """ = cmds.listConnections( self._attribute, s=True, d=False) """
        return inputs_of(self)

    def outputs(self):
        """ = cmds.listConnections( self._attribute, d=True, s=False) """
        return outputs_of(self)

    def __rshift__(self, other):
        # supports pymel-style connection syntax, ie.   this.tx >> that.ty
        connect(self, other)

    def __floordiv__(self, other):
        # supports pymel-style disconnection syntax, ie. this.x // that.ty
        disconnect(self, other)

    @property
    def locked(self):
        return cmds.getAttr(self._attribute, lock=True)

    @locked.setter
    def locked(self, val):
        cmds.setAttr(self._attribute, lock=val)

    @property
    def keyable(self):
        return cmds.getAttr(self._attribute, keyable=True)

    @keyable.setter
    def keyable(self, val):
        cmds.setAttr(self._attribute, keyable=val)

    @property
    def channelbox(self):
        return cmds.getAttr(self._attribute, cb=True)

    @keyable.setter
    def channelbox(self, val):
        cmds.setAttr(self._attribute, cb=val)

    @property
    def size(self):
        return cmds.getAttr(self._attribute, size=True)


class NamedNumber(float, Connectable):
    """wraps floats and doubles"""
    __slots__ = ['_attribute']

    def __new__(cls, arg, *_):
        return float.__new__(NamedNumber, arg)

    def __init__(self, arg, _attribute):
        self._attribute = _attribute


class NamedInt(int, Connectable):
    """wraps longs, shorts, bytes and ints"""
    __slots__ = ['_attribute']

    def __new__(cls, arg, *_):
        return int.__new__(NamedInt, arg)

    def __init__(self, arg, _attribute):
        self._attribute = _attribute


class NamedTuple(tuple, Connectable):
    """wraps multi-value numeric attributes, eg 'double2'"""

    # no slots, because tuple doesn't support them
    # but these attributes are usually not perf-sensitive

    def __new__(self, arg, _attribute):
        return tuple.__new__(NamedTuple, arg)

    def __init__(self, arg, _attribute):
        self._attribute = _attribute


class NamedMulti(dict, Connectable):
    """Wraps multiattributes (maya attributes with the -multi flag)"""

    __slots__ = ['_attribute', '_type']

    def __init__(self, arg, _attribute, type=None):
        self._attribute = _attribute
        self.update(arg)
        self._type = type

    def __getitem__(self, index):
        if not index in self:
            raise UnsetIndexError("{} has no data at index {}".format(self._attribute, index))
        return dict.__getitem__(self, index)

    def __setitem__(self, index, val):
        if self._type:
            cmds.setAttr("{}[{}]".format(self._attribute, index), val, type=self._type)
        else:
            cmds.setAttr("{}[{}]".format(self._attribute, index), val)

    def __delitem__(self, index):
        raise NotImplementedError("Can't delete index of a multi-attribute")


class NamedVector(MVector, Connectable):
    """Wraps double3 and float3 attributes as MVectors"""
    __slots__ = ['_attribute']

    def __init__(self, arg, _attribute):
        MVector.__init__(self, arg)
        self._attribute = _attribute

    def __repr__(self):
        return MVector.__repr__(self) + " (" + self._attribute + ")"


class NamedMatrix(MMatrix, Connectable):
    """Wraps matrix attributes"""
    __slots__ = ['_attribute']

    def __init__(self, arg, _attribute):
        MMatrix.__init__(self, arg)
        self._attribute = _attribute


class NamedOther(str, Connectable):
    """Wraps string attributes"""
    # no slots for subtypes of __str__

    def __new__(self, arg, _attribute):
        return str.__new__(NamedOther, arg)

    def __init__(self, arg, _attribute):
        self._attribute = _attribute


class NamedUnsupported(Connectable):
    """wraps attributes that can't be set, but can be connected"""
    __slots__ = ['_attribute']

    def __init__(self, attribute):
        self._attribute = attribute

    def __repr__(self):
        return "<maya native attribute '{}'>".format(self._attribute)


"""
The `make_descriptor` and `make_xform_descriptor` classes create python property descriptors
to enable dot-property access syntax:

     >> print this.rotateAxis  
     >> (0,0,0)

     >> this.rotateAxes = (45, 45, 0)

 The 'make_descriptor' variety wraps calls to `getAttr()` and `setAttr()`.  The
 'make_xform_descriptor' variety uses calls to `xform()`, which allows getting and
 setting values in either world or local space.
"""


def make_descriptor(at_name, at_type):
    """
    Creates python descriptor objects that use getAttr and setAttr
    to allow dotted property access to scene objects.

    The individual functions are mostly there to handle correct
    return types and the vagaries of how maya returns queries.

    The layout of this code is less readable than would be ideal; minimizing
    variables in the getters /setters and relying on the closure to
    format the names is very important for speed.
    """

    def dotted(obj):
        return ".".join((obj, at_name))

    def set_array_attr(self, obj, val):
        cmds.setAttr(dotted(obj), len(val), *val, type=at_type)

    def set_tuple_attr(self, obj, val):
        cmds.setAttr(dotted(obj), *val, type=at_type)

    def set_typed_attr(self, obj, val):
        cmds.setAttr(dotted(obj), val, type=at_type)

    def set_bool_attr(self, obj, val):
        cmds.setAttr(dotted(obj), bool(val))

    def set_default_attr(self, obj, val):
        cmds.setAttr(dotted(obj), val)

    def set_matrix_attr(self, obj, val):
        cmds.setAttr(dotted(obj), *val, type='matrix')

    def set_enum_attr(self, obj, val):
        if isinstance(val, numbers.Number):
            cmds.setAttr(dotted(obj), int(val))
        else:
            enums = cmds.attributeQuery(self.attribute, n=obj, le=True)[0].split(":")
            try:
                cmds.setAttr(dotted(obj), enums.index(val))
            except ValueError:
                raise InvalidEnumError("enum value '{}' is invalid".format(val))

    def set_compound_attr(self, obj, val):
        raise NotImplementedError("Compound attributes are not supported in this release")

    def unsupported(self, obj, val):
        raise ReadOnlyPropertyError("maya.cmds cannot set attribute '{}'".format(dotted(obj)))

    set_functions = {
        'bool': set_bool_attr,
        'enum': set_enum_attr,
        'string': set_typed_attr,
        'stringArray': set_array_attr,
        'compound': unsupported,
        'message': unsupported,
        'matrix': set_matrix_attr,
        'fltMatrix': set_matrix_attr,
        'reflectanceRGB': unsupported,
        'reflectance': unsupported,
        'spectrumRGB': unsupported,
        'spectrum': unsupported,
        'float2': set_tuple_attr,
        'float3': set_tuple_attr,
        'double2': set_tuple_attr,
        'double3': set_tuple_attr,
        'long2': set_tuple_attr,
        'long3': set_tuple_attr,
        'short2': set_tuple_attr,
        'short3': set_tuple_attr,
        'doubleArray': set_array_attr,
        'int32Array': set_array_attr,
        'vectorArray': unsupported,
        'nurbsCurve': unsupported,
        'nurbsSurface': unsupported,
        'mesh': unsupported,
        'lattice': unsupported,
        'pointArray': unsupported,
    }

    # for all numeric types, bools,
    def getter(slf, obj, _):
        attrib_value = cmds.getAttr(dotted(obj), silent=True)

        if isinstance(attrib_value, numbers.Number):
            return NamedNumber(attrib_value, dotted(obj))

        multi = cmds.attributeQuery(at_name, node=obj, multi=True)
        if not multi:
            raise AttributeTypeError("non-numeric attribute found, expected multi")

        multi_indices = iter(cmds.getAttr(dotted(obj), multiIndices=True))
        vdict = itertools.izip(multi_indices, attrib_value[0])
        return NamedMulti(vdict, dotted(obj))

    def enum_getter(_self, obj, _):
        # always returns enums as strings
        return cmds.getAttr(dotted(obj), asString=True)

    def vector_getter(_self, obj, _):
        # return 3-tuples as MVectors.  Note the unpacking!
        return NamedVector(cmds.getAttr(dotted(obj))[0], dotted(obj))

    def matrix_getter(_self, obj, _):
        return NamedMatrix(cmds.getAttr(dotted(obj)), dotted(obj))

    def int_getter(_self, obj, _):
        return NamedInt(cmds.getAttr(dotted(obj)), dotted(obj))

    def tuple_getter(_self, obj, _):
        # note unacking
        return NamedTuple(cmds.getAttr(dotted(obj))[0], dotted(obj))

    def string_getter(_self, obj, _):
        is_multi = cmds.attributeQuery(at_name, node=obj, multi=True)

        if not is_multi:
            return NamedOther(cmds.getAttr(dotted(obj)), dotted(obj))
        indices = cmds.getAttr(dotted(obj), multiIndices=True) or []

        def index_get(num):
            return ''.join((dotted(obj), '[', str(num), ']'))

        vdict = ((m, cmds.getAttr(index_get(m))) for m in indices)
        return NamedMulti(vdict, dotted(obj), type='string')

    # for values user cannot edit or query,
    # but may want to use for connections or introspection
    def unsupported_getter(_self, obj, _):
        return NamedUnsupported(dotted(obj))

    get_functions = {
        'double3': vector_getter,
        'double3Linear': vector_getter,
        'double3Angle': vector_getter,
        'float3': vector_getter,
        'enum': enum_getter,
        'matrix': matrix_getter,
        'bool': int_getter,
        'short': int_getter,
        'byte': int_getter,
        'double2': tuple_getter,
        'float2': tuple_getter,
        'long2': tuple_getter,
        'short2': tuple_getter,
        'long3': tuple_getter,
        'int32Array': tuple_getter,
        'doubleArray': tuple_getter,
        'string': string_getter,
        'stringArray': tuple_getter,
        'vectorArray': unsupported_getter,
        'nurbsCurve': unsupported_getter,
        'nurbsSurface': unsupported_getter,
        'mesh': unsupported_getter,
        'lattice': unsupported_getter,
        'pointArray': unsupported_getter
    }

    class AnonymousDescriptor(object):
        attribute = at_name
        __get__ = get_functions.get(at_type, getter)
        __set__ = set_functions.get(at_type, set_default_attr)

        def __repr__(self):
            return "property descriptor ({})".format(self.attribute)

    return AnonymousDescriptor()


def make_xform_descriptor(flag, return_type=MVector, worldspace=False, plug="", readonly=False):
    """
    Creates accessors that use the xform command instead of getAttr/setAttr

    These are better for moving rotating and so on, since they can be done in
    either world or local space.

    <return_type> specifies the type of the returnValue (MVectors or MMatrices)

    if <worldspace> is true, return values in world space; otherwise in local space

    if <readonly> is true, the attribute cannot be assigned to (this is primarily
    used for world space scales, which can't be set in Maya)

    <plug> specifies the name of the attribute to use for connections. If plug
    is an empty string (the default) the attribute is not connectable.
    """

    def xform_getter(self, obj, _type):
        result = cmds.xform(obj, **{'q': True, flag: True, "ws": worldspace})
        if return_type is MVector:
            return NamedVector(result, ".".join((obj, plug)))
        else:
            return NamedMatrix(result, ".".join((obj, plug)))

    def xform_setter(self, obj, val):
        if readonly:
            raise ReadOnlyPropertyError("Maya cannot assign an absolute value to " + flag)
        cmds.xform(obj, **{flag: val, "ws": worldspace})

    class XformDescriptor(object):
        attribute = flag
        __get__ = xform_getter
        __set__ = xform_setter

        def __repr__(self):
            return 'xform descriptor ({})'.format(self.attribute)

    return XformDescriptor()


class Nodule(str):
    """
    base class for nodule objects. They look like strings as far as `ls()` and
    other commands are concerned, but use python descriptors to allow dotted
    property access.

    Because nodules are strings, they are immutable. If the underlying object is renamed
    this instance is invalidated, the instance will no longer function. To rename an 
    existing object, capture the results of 'rename'

        fred = rename(fred, "my_new_name")

    Nodule objects truth test based on whether or not the object is present in the
    maya scene.  So

        if fred:
            print "object " + fred + "exists"
        else:
            print "object" + fred + "has been deleted"

    Nodule objects return the node type of the underlying maya object as a string
    property.  Nonexistent objects return None

        >> fred.type
        >> 'transform'

        >> barney.type
        >> 'mesh'

        >> deleted.type
        >> None

    """

    # this masks the fact that vanilla strings have a translate method, which
    # we may need for the maya 'translate' property.  This does mean that
    # non-transform nodes may try to call 'translate'
    _translate = str.translate
    translate = make_descriptor('translate', 'double3Linear')

    # Each subclass maintains a class-level dictionary of descriptors, keyed by
    # attribute name
    LOOKUPS = {}

    @property
    def type(self):
        try:
            return cmds.nodeType(self)
        except RuntimeError:
            return None

    @property
    def uuid(self):
        try:
            return cmds.ls(self, uuid=True)[0]
        except IndexError:
            return None

    def add_attribute(self, name, **kwargs):
        """
        adds an attribute named 'name' with the same keyword args as cmds.addAttr
        """
        kwargs['ln'] = name      # supplied is always the 'long' name

        if 'longName' in kwargs:
            del kwargs['longName']    # avoid duplicates
        cmds.addAttr(self, **kwargs)
        return self.get_named_attr(name)

    def delete_attribute(self, name):
        cmds.deleteAttr(".".join(self, name))

    def get_named_attribute(self, attrib_name):
        """
        get an attribute value using a string name known only at runtime
        """
        return self.__getattr__(attrib_name)

    def set_named_attribute(self, attrib_name, value):
        """
        set an attribute value using a string name known only at runtime
        """
        self.__setattr__(attrib_name, value)

    def __getattr__(self, name):

        accessor = self.__class__.__dict__.get(name, self.LOOKUPS.get(name))
        if accessor:
            return accessor.__get__(self, None)
        else:
            self._cache_attribute(name)
            return self.LOOKUPS[name].__get__(self, None)

    def __setattr__(self, name, val):

        accessor = self.__class__.__dict__.get(name, self.LOOKUPS.get(name))
        if accessor:
            return accessor.__set__(self, val)
        else:
            self._cache_attribute(name)
            return self.LOOKUPS[name].__set__(self, val)

    def _cache_attribute(self, at_name):

        try:
            canonical, at_type = cmds.ls(".".join((self, at_name)), showType=True)
            canonical = canonical.split(".")[-1]

        except ValueError as e:
            if e.message == 'need more than 0 values to unpack':
                raise NoMayaAttributeError("'{}' has no attribute '{}'".format(self, at_name))
            else:
                raise

        self.LOOKUPS[at_name] = self.LOOKUPS[canonical] = make_descriptor(at_name, at_type)

        return self.LOOKUPS[at_name]

    def __repr__(self):
        if self.type:
            quoted = "'" + self + "'"
            return self.type + "(" + quoted + ")"
        else:
            return "invalid nodule (" + quoted + ")"

    def __nonzero__(self):
        return cmds.objExists(self)


class TransformNodule(Nodule):
    """
    wraps a maya transform.  Exposes local and world space versions of the key transform attributes.transform
    """

    LOOKUPS = {}

    local_position = make_xform_descriptor('t', return_type=MVector, worldspace=False, plug='translate')
    local_rotation = make_xform_descriptor('ro', return_type=MVector, worldspace=False, plug='rotate')
    local_scale = make_xform_descriptor('scale', return_type=MVector, worldspace=False, plug='scale')
    local_matrix = make_xform_descriptor('matrix', return_type=MMatrix, worldspace=False, plug='matrix')
    local_rotate_pivot = make_xform_descriptor('rp', return_type=MVector, worldspace=False, plug='rotatePivot')
    local_scale_pivot = make_xform_descriptor('sp', return_type=MVector, worldspace=False, plug='scalePivot')

    world_position = make_xform_descriptor('t', return_type=MVector, worldspace=True)
    world_rotation = make_xform_descriptor('ro', return_type=MVector, worldspace=True)
    world_scale = make_xform_descriptor('scale', return_type=MVector, worldspace=True, readonly=True)
    world_matrix = make_xform_descriptor('matrix', return_type=MMatrix, worldspace=True, plug='worldMatrix')
    world_rotate_pivot = make_xform_descriptor('rp', return_type=MVector, worldspace=True)
    world_scale_pivot = make_xform_descriptor('sp', return_type=MVector, worldspace=True)

    rotate_axis = ra = make_descriptor('rotateAxis', 'double3')
    rotate_order = ro = make_descriptor('rotateOrder', 'enum')

    @property
    def shape(self):
        shapes = cmds.listRelatives(self, s=True, ni=True)
        if shapes:
            return nodule(shapes[0])
        return None

    @property
    def children(self):
        kids = cmds.listRelatives(self, c=True, type='transform') or []
        return tuple(TransformNodule(t) for t in kids)

    @property
    def descendants(self):
        descendants = sorted(cmds.listRelatives(self, ad=True, type='transform') or [])
        return tuple(TransformNodule(t) for t in descendants)

    @property
    def parent(self):
        p = cmds.listRelatives(self, p=True)
        if p:
            return TransformNodule(p[0])
        return None


class JointNodule (TransformNodule):
    joint_orient = jo = make_descriptor('scale', 'double3')


# global dictionary of nodetype -> maya class string relationships
# add specialized node types with register_nodule_class

SPECIALTIES = {
    'transform': TransformNodule,
    'joint': JointNodule
}


"""
Nodule-specific exception types
"""


class NoMayaObjectError (TypeError):
    """Tried to create nodule for a non-existent object"""
    pass


class NoMayaAttributeError(AttributeError):
    """Tried to access an object is not present"""
    pass


class AttributeTypeError(AttributeError):
    """Tried to access an attribute using the data type"""
    pass


class InvalidEnumError(ValueError):
    """Tried to set an invalid enum value"""
    pass


class ReadOnlyPropertyError(TypeError):
    """Tried to set a locked or connected attribute"""
    pass


class AttributeConnectionError(RuntimeError):
    """Attribute could not be connected"""
    pass


class UnsetIndexError(KeyError):
    """Tried to set an indexed attribute with an invalid index"""
    pass


__all__ = (
    'nodule',
    'nodule_from_uuid',
    'nodules_from_list',
    'rename',
    'connect',
    'disconnect',
    'inputs_of',
    'outputs_of',
    'address_of',
    'register_nodule_class',
    'NoMayaObjectError',
    'NoMayaAttributeError',
    'InvalidEnumError',
    'AttributeConnectionError',
    'ReadOnlyPropertyError'
)
