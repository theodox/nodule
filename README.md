# Nodule

Pythonic property access to maya nodes; aka "Pymel without the pymel"

The purpose of this module is to eliminate the clutter that comes from accessing the properties of maya objects using `maya.cmds`.   Maya wants you to get properties like this:

     position = cmds.getAttr(my_object + ".translate")
     
 and set them like this:

     cmds.setAttr(my_object + ".stringAttr", "new_string", type="string")

and connect them like this:

    cmds.connectAttr (this_object + ".rotateX", that_object + ".rotateY")

 using Nodule that looks like

     position = my_object.translate
     my_object.stringAttr = 'new_string'
     connect (this_object.rotateX, that_object.rotateY)

Pymel has offered a similar facility for a long time -- however to use that facility you have to use the large and complicated pymel ecosystem.  Nodule offers a much more limited feature set, but in a lighter and faster package.

## Installation

Nodule is a single-file python module. Place it anywhere on your Maya's python path.

## Basic usage

The primary interface is the function `nodule()`, which takes a maya string name and returns an object which can dynamically access properties on that object:

    from nodule import nodule
    cube_name, _ = cmds.polyCube()
    my_cube = nodule(cube_name)

my_object is a sub-type of string, so you can use it pass it to any maya command that expects a string object name:

    cmds.objectExists(my_cube)
    # Result: True #  

    cmds.ls(my_cube)
    # Result: [u'pCube1'] # 

However the new object can dynamically get and set properties on the maya node 'pCube1'.  For example:

    # hide  it
    my_cube.visibility = False

    # show it again
    my_cube.visibility = True

Under the hood these two line were actually calling `cmds.getAttr` and `cmds.setAttr` with the appropriate flags and arguments.  Nodules can access both built-in and user-defined properties.  

### Connecting attributes

If you want to connect attributes on a nodule, you can use the property references directly

     connect (nodule_1.translateX, nodule_2.rotateY)

If you need to mix and match nodules with strings, you can:

    connect (nodule_1.translateY, "pCube99.scaleZ")
    connect ('ambientLight1.intensity', nodule_3.light_compensation)

Disconnecting works the same way:

    disconnect (nodule_1.translateX, nodule_2.rotateY)

### Locking and  hiding attributes

You can lock or unlock attributes like this:

    nodule_1.translate.locked = True
    nodule_1.translate.locked = False

You can set them keyable...

    nodule_1.translate.keyable = True
    nodule_1.translate.keyable = False

and Add or remove them from channel box:

    nodule_1.translate.channelbox = True
    nodule_1.translate.channelbox = False

## Transform nodules

Most nodule properties are just translations of calls to `getAttr` and `setAttr`.  However nodules that wrap Maya transform nodes have special properties to make it easier to do common jobs.  There are local and worldspace versions of the following properties:

* `local_position` and `world_position` get or set the object's position
* `local_rotation` and `world_rotation` get or set rotation
* `local_scale` and `world_scale` get the scale.  Maya does not allow you to set world scale directly, however, so `world_scale` is read-only. 
* `local_matrix` and `world_matrix`  get and set the node matrix

There are also `local_rotate_pivot`, `local_scale_pivot`, `world_rotate_pivot` and `world_scale_pivot`

All of these attributes can be set with lists, tuples, or [Maya MVectors](https://knowledge.autodesk.com/search-result/caas/CloudHelp/cloudhelp/2018/ENU/Maya-SDK/py-ref/class-open-maya-1-1-m-vector-html.html).  

    my_nodule.world_position = 3,2,1
    my_nodule.world_position = (0,0,0)
    my_nodule.world_position = [-1,-1,-1]
    my_nodule.world_position = MVector(5.0, 4.0, 3.0)

They return [Maya MVectors](https://knowledge.autodesk.com/search-result/caas/CloudHelp/cloudhelp/2018/ENU/Maya-SDK/py-ref/class-open-maya-1-1-m-vector-html.html), so you can do vector or matrix math on the results.  MVectors also let you access x, y and z components by name:

    my_nodule.local_position
    # Result: maya.api.OpenMaya.MVector(1, 2, 4) (pCube1.) # 

    my_nodule.local_position.z
    # Result: 4.0 # 

`local_matrix` and `world_matrix` return Maya `MMatrix` objects.


#### .shape

Transform nodules have a `.shape` property, which returns a nodule for the shape (if any) attached to the transform:

    my_cube.shape
    # Result: mesh('pCubeShape1') # 

_Note:_ If a transform has multiple shapes, `.shape` only returns the first.

#### .parent

Returns a nodule for the parent of this transform, or None if this nodule is a child of the world.

#### .children

Returns nodules for all of the transform children (_not_ shapes) of this transform.

#### descendants:

Returns nodules for all of the transforms below this nodule in the hierarchy -- equivalent to `cmds.listRelatives(nodule, ad=True, type='transform')`

## Other nodule features

Besides property access, nodules have a couple of other convenience features:

#### Truth-testing

If you if-check an nodule object, it will return `True` if the maya object it points at still exists in the scene and `False` if it does not:

    if not my_nodule:
       print my_nodule + " has been deleted"

#### .uuid

You can get the uuid of a maya node from a nodule like this:

    my_nodule.uuid
    # Result: 3017CF64-E54B-303A-C0BF-639553362236 #

`.uuid` is a read-only property

#### .type

You can get the maya node type of a nodule with the 'type' property:

    my_nodule.type
    # Result: 'mesh'

`.type` is a read-only property


#### enum properties

Any enum properties are gotten and set as strings, not numbers:

    my_nodule.rotateOrder = 'xyz'


#### Runtime attributes

Sometimes it's not possible to know what attributes you need until runtime.  If you need to get or set a property dynamically you can uses the functions `get_named_attribute()` and `set_named_attribute()` to manage attribute values with string names:

    my_nodule.get_named_attribute('bar')
    my_nodule.set_named_attribute('foo', 75)

You can also use the builtin Python functions `getattr` and `setattr` (note the capitalization -- these are not the same as the Maya versions):

    getattr(my_nodule, 'some_attr')
    setattr(my_nodule, 'other_attr', 999)

#### Custom attributes

You can add a custom attribute to a nodule object like this:

    my_nodule.add_attribute("custom")
    my_nodule.custon
    # Result: 0  #
    my_nodule.custom = -1

`add_attribute()` takes the same flags as `cmds.addAttr`, except that it always uses the first argument as the long name.

You can also delete an attribute like this:

     my_nodule.delete_attribute("custom")

## Functions:

These are the functions exposed in this module:

### creating nodules
`nodule()`  returns the appropriate nodule for a supplied object
`nodule_from_uuid()`  returns a nodule from a maya uuid string
`nodules_from_list()` a generator that yields nodules from a list or iterable input
`rename()`  renames the supplied nodule and returns the renamed object.  Nodules are like strings -- if the underlying Maya object is renamed the nodule will no longer be able to work with it, so use `rename()` and capture the result:
    
    my_nodule = rename(my_nodule, "new_name_#")

### Attributes

`connect()` and `disconnect()` connect or disconnect attributes.
`inputs_of()` and `outputs_of()` return the nodes are connected to the input or output of an attribute:

      inputs_of(my_cube.shape.inMesh)
      # Result: (polyCube('polyCube1'),) # 

`address_of()`  returns the string name of an attribute.

     address_of(my_nodule.translate)
     # Result: 'pCube1.translate'

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

A tip of the hat to the developers of Pymel, who showed that there was life beyond maya.cmds.

