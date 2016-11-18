

# from .typereader import Property, allow_properties, reads_type
# from collections import namedtuple

from .typereader import reads_type, get_type_reader, readMatrixf, readMatrixd
from .basereader import BaseReader

from collections import namedtuple, OrderedDict
import struct

VertexFormat = namedtuple("VertexFormat", ["position", "normal", "texture"])

def read_named_type(reader):
  """Reads a typename, and then reads the type named"""
  typename = reader.read_string()
  return get_type_reader(typename)(reader)

def read_string_uint_dict(stream):
  """Reads a dictionary of type String : uint"""
  length = stream.read_uint()
  data = OrderedDict()
  for _ in range(length):
    key = stream.read_string()
    value = stream.read_uint()
    data[key] = value
  return data

def read_property_list(stream):
  """Reads a typed list of properties and returns as an ordered dict"""
  length = stream.read_uint()
  data = OrderedDict()
  for _ in range(length):
    prop = read_named_type(stream)
    data[prop.name] = prop.value
  return data

class EDMFile(object):
  def __init__(self, filename):
    reader = BaseReader(filename)
    reader.read_constant(b'EDM')
    self.version = reader.read_ushort()
    assert self.version == 8, "Unexpected .EDM file version"
    # Read the two indexes
    self.indexA = read_string_uint_dict(reader)
    self.indexB = read_string_uint_dict(reader)
    self.node = read_named_type(reader)
    assert reader.read_int() == -1
    reader.read(1648)

    # Now read the connectors/rendernode list
    objects = {}
    for _ in range(reader.read_uint()):
      name = reader.read_string()
      objects[name] = reader.read_list(read_named_type)
    assert len(objects) == 2
    self.connectors = objects["CONNECTORS"]
    self.renderNodes = objects["RENDER_NODES"]

    # Verify we are at the end of the file without unconsumed data.
    endPos = reader.tell()
    if len(reader.read(1)) != 0:
      print("Warning: Ended parse at {} but still have data remaining".format(endPos))

@reads_type("model::RootNode")
class RootNode(object):
  unknown_parts = []
  @classmethod
  def read(cls, stream):
    self = cls()
    self.name = stream.read_string()
    self.version = stream.read_uint()
    self.properties = read_property_list(stream)
    self.unknown_parts.append(stream.read(145))
    self.materials = stream.read_list(Material.read)
    self.unknown_parts.append(stream.read(8))
    self.nodes = stream.read_list(read_named_type)
    return self

@reads_type("model::BaseNode")
class BaseNode(object):
  @classmethod
  def read(cls, stream):
    node = cls()
    node.base_data = stream.read_uints(3)
    return node

@reads_type("model::Node")
class Node(BaseNode):
  pass

@reads_type("model::TransformNode")
class TransformNode(BaseNode):
  @classmethod
  def read(cls, stream):
    self = super(TransformNode, cls).read(stream)
    self.matrix = readMatrixd(stream)
    return self

@reads_type("model::ArgRotationNode")
class ArgRotationNode(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.name = stream.read_string()
    self.base_data = stream.read(248)
    assert stream.read_uint() == 0
    self.rotData = stream.read_list(cls._read_AANRotationArg)
    assert stream.read_uint() == 0
    return self

  @classmethod
  def _read_AANRotationArg(cls, stream):
    arg = stream.read_uint()
    count = stream.read_uint()
    data = stream.read(40*count)
    return (arg, count, data)

@reads_type("model::ArgPositionNode")
class ArgPositionNode(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.name = stream.read_string()
    self.base_data = stream.read(248)
    self.posData = stream.read_list(cls._read_AANPositionArg)
    self.unknown = stream.read_uints(2)
    return self
    
  @classmethod
  def _read_AANPositionArg(cls, stream):
    arg = stream.read_uint()
    count = stream.read_uint()
    data = stream.read(32*count)
    return (arg, count, data)

@reads_type("model::ArgScaleNode")
class ArgScaleNode(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.name = stream.read_string()
    self.base_data = stream.read(248)
    # ASSUME that it is layed out in a similar way, but have no non-null examples.
    # So, until we do, assert that this is zero always
    assert all(x == 0 for x in stream.read(12))
    return self

@reads_type("model::ArgAnimationNode")
class ArgAnimationNode(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.name = stream.read_string()
    self.base_data = stream.read(248)
    self.posData = stream.read_list(ArgPositionNode._read_AANPositionArg)
    self.rotData = stream.read_list(ArgRotationNode._read_AANRotationArg)
    assert stream.read_uint() == 0
    return self

@reads_type("model::ArgVisibilityNode")
class ArgVisibilityNode(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.name = stream.read_string()
    self.unknown = stream.read(8)
    self.visData = stream.read_list(cls._read_AANVisibilityArg)
    return self

  @classmethod
  def _read_AANVisibilityArg(cls, stream):
    arg = stream.read_uint()
    count = stream.read_uint()
    data = stream.read(16*count)
    return (arg, count, data)

def _read_material_VertexFormat(reader):
  channels = reader.read_uint()
  # data = [int(x) for x in reader.read(channels)]
  data = reader.read(channels)
  # Ensure we don't have any unknown values
  assert data[2:4] == b'\x00\x00'
  assert all(x == 0 for x in data[5:])
  vf = VertexFormat(position=int(data[0]), normal=int(data[1]), texture=int(data[4]))
  return vf

def _read_material_texture(reader):
  reader.read_constant(b"\x00\x00\x00\x00\xff\xff\xff\xff")
  name = reader.read_string()
  reader.read_constant(b"\x02\x00\x00\x00\x02\x00\x00\x00\n\x00\x00\x00\x06\x00\x00\x00")
  matrix = readMatrixf(reader)
  return (name, matrix)

# Lookup table for material reading types
_material_entry_lookup = {
  "BLENDING": lambda x: x.read_uchar(),
  "CULLING" : lambda x: x.read_uchar(),
  "DEPTH_BIAS": lambda x: x.read_uint(),
  "TEXTURE_COORDINATES_CHANNELS": lambda x: x.read(52),
  "MATERIAL_NAME": lambda x: x.read_string(),
  "NAME": lambda x: x.read_string(),
  "SHADOWS": lambda x: x.read_uchar(),
  "VERTEX_FORMAT": _read_material_VertexFormat,
  "UNIFORMS": read_property_list,
  "ANIMATED_UNIFORMS": read_property_list,
  "TEXTURES": lambda x: x.read_list(_read_material_texture)
}

class Material(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    props = OrderedDict()
    for _ in range(stream.read_uint()):
      name = stream.read_string()
      props[name] = _material_entry_lookup[name](stream)
    self.props = props
    return self


@reads_type("model::Connector")
class Connector(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.name = stream.read_string()
    self.data = stream.read(16)
    return self

uint_negative_one = struct.unpack("<I", struct.pack("<i", -1))[0]

@reads_type("model::RenderNode")
class RenderNode(BaseNode):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.name = stream.read_string()
    super(RenderNode, cls).read(stream)
    self.material = stream.read_uint()
    self.intData = stream.read_list(cls._read_int_section)
    self.vertexCount = stream.read_uint()
    self.vertexStride = stream.read_uint()
    # Read and group this according to stride
    vtx = stream.read_floats(self.vertexCount * self.vertexStride)
    n = self.vertexStride
    self.vertexData = [vtx[i:i+n] for i in range(0, len(vtx), n)]

    # Now read the index data
    dataType = stream.read_uchar()
    entries = stream.read_uint()
    assert stream.read_uint() == 5
    if dataType == 0:
      self.indexData = stream.read_uchars(entries)
    elif dataType == 1:
      self.indexData = stream.read_ushorts(entries)
    else:
      raise IOError("Unknown vertex index type '{}'".format(dataType))
    return self

  @classmethod
  def _read_int_section(cls, stream):
    # Read uint values until we get -1 (signed)
    # This will either be <uint> <-1> or <uint> <uint> <-1>
    def _read_to_next_negative():
      data  = stream.read_uint()
      if data == uint_negative_one:
        return []
      else:
        return [data] + _read_to_next_negative()
    section = _read_to_next_negative()
    assert len(section) == 1 or len(section) == 2
    return section

