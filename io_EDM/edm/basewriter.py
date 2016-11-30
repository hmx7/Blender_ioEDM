
import struct
from collections import Counter

from mathtypes import matrix_to_sequence

class BaseWriter(object):
  def __init__(self, filename):
    self.filename = filename
    self.stream = open(filename, "wb")
    self.typeLog = Counter()

  def close(self):
    self.stream.close()

  def write(self, data):
    self.stream.write(data)

  def write_uchar(self, value):
    self.stream.write(struct.pack("B", value))

  def write_uchars(self, values):
    self.stream.write(struct.pack("{}B".format(len(value)), *value))

  def write_ushort(self, value):
    self.stream.write(struct.pack("<H", value))

  def write_ushorts(self, values):
    self.stream.write(struct.pack("<{}H".format(len(value)), *value))

  def write_uint(self, value):
    self.stream.write(struct.pack("<I", value))

  def write_uints(self, values):
    self.stream.write(struct.pack("<{}I".format(len(value)), *value))

  def write_int(self, value):
    self.stream.write(struct.pack("<i", value))

  def write_ints(self, values):
    self.stream.write(struct.pack("<{}i".format(len(value)), *value))

  def write_float(self, value):
    self.stream.write(struct.pack("<f", value))

  def write_floats(self, values):
    self.stream.write(struct.pack("<{}f".format(len(value)), *value))

  def write_double(self, value):
    self.stream.write(struct.pack("<d", value))

  def write_doubles(self, values):
    self.stream.write(struct.pack("<{}d".format(len(value)), *value))

  def write_string(self, value):
    data = value.encode("windows-1251")
    self.write_uint(len(data))
    self.write(data)

  def write_list(self, data, writer):
    self.write_uint(len(data))
    for entry in data:
      writer(self, entry)

  def write_vec2f(self, vector):
    self.write_floats([vector[0], vector[1]])
  
  def write_vec3f(self, vector):
    self.write_floats([vector[0], vector[1], vector[2]])

  def write_vec3d(self, vector):
    self.write_doubles([vector[0], vector[1], vector[2]])

  def write_matrixf(self, matrix):
    self.write_floats(matrix_to_sequence(matrix))

  def write_matrixd(self, matrix):
    self.write_doubles(matrix_to_sequence(matrix))

  def write_quaternion(self, quat):
    self.write_doubles([quat[1], quat[2], quat[3], quat[0]])

  def mark_written(self, name, count=1):
    self.typeLog(name) += count