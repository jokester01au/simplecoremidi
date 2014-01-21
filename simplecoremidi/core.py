from . import _simplecoremidi as cfuncs
import logging

class MIDISource(object):
  def __init__(self, name, source_ref):
    self.name = name
    self._source_ref = source_ref
    self.__source = None

  @classmethod
  def list(cls):
      return [MIDISource(cfuncs.get_midi_endpoint_name(i), i)
           for i in cfuncs.get_midi_source_list()
      ]

  def _source(self):
    if not self.__source:
        self.__source = cfuncs.get_midi_source(self._source_ref)
    if not self.__source:
       raise Exception('Source %s unavailable' % self.name)
    return self.__source

  def receive(self, timeout=1):
    """
    this will block until data is available
    """
    bytes = cfuncs.receive_midi(self._source(), timeout)
    if not bytes:
        return None
    return Message.parse_message(bytes)

  def __str__(self):
      return self.name

class MIDIDestination(object):
  def __init__(self, name, destination_ref):
    self.name = name
    self._destination_ref = destination_ref
    self.__destination = None

  def _destination(self):
    if not self.__destination:
        self.__destination = cfuncs.get_midi_destination(self._destination_ref)
    if not self.__destination:
       raise Exception('Destination %s unavailable' % self.name)
    return self.__destination

  def send(self, message):
      logging.debug (message, map(hex,message.toBytes()))
      return cfuncs.send_midi(self._destination(), message.toBytes())

  @classmethod
  def list(cls):
      return [MIDIDestination( cfuncs.get_midi_endpoint_name(i), i)
           for i in cfuncs.get_midi_destination_list()
      ]

  def __str__(self):
      return self.name


class Message(object):
  NOTE_OFF = 0x80
  NOTE_ON = 0x90
  CONTROL_CHANGE = 0xB0
  PROGRAM_CHANGE = 0xC0

  def fromBytes(self, bytes):
      self.message_type = bytes[0] & 0xF0
      self.channel = bytes[0] & 0x0F

  def toBytes(self):
     if self.channel == -1 or self.message_type == -1:
         raise Exception('Message is not initialised')
     return [self.message_type | self.channel]

  def __init__(self, message_type=0, channel=1):
      self.message_type = message_type
      self.channel = channel

  def __str__(self):
     # fixme this doesn't work if intermediate classes don't know whether to add the closing parenthesis
     return "{}(channel = {}".format(self.__class__.__name__, self.channel)

  @classmethod
  def parse_message(cls, bytes):
      message_type = bytes[0] & 0xF0
      if message_type == cls.NOTE_OFF:
        return NoteOffMessage().fromBytes(bytes)
      elif message_type == cls.NOTE_ON:
        return NoteOnMessage().fromBytes(bytes)
      elif message_type == cls.PROGRAM_CHANGE:
        return ProgramChangeMessage().fromBytes(bytes)
      elif message_type == cls.CONTROL_CHANGE:
        return ControllerChangeMessage().fromBytes(bytes)
      else:
        return UnknownMessage().fromBytes(bytes)


class NoteMessage(Message):
    def __init__(self, type=-1, channel=-1, number=-1, velocity=-1):
        super(NoteMessage, self).__init__(type, channel)
        self.number = number
        self.velocity = velocity

    def __str__(self):
        return "{}, number = {}, velocity = {})".format(super(NoteMessage, self).__str__(), self.number, self.velocity)

    def toBytes(self):
        if self.number == -1:
            raise Exception('Message is not initialised')
        return super(NoteMessage, self).toBytes() + [self.number, self.velocity]

    def fromBytes(self, bytes):
        super(NoteMessage, self).fromBytes(bytes)
        self.number = bytes[1]
        self.velocity = bytes[2]
        return self

    def is_note_off(self):
        return self.velocity == 0 or self.message_type == self.NOTE_OFF

class NoteOffMessage(NoteMessage):
  def __init__(self, channel=-1, number=-1, velocity=-1):
      super(NoteOffMessage, self).__init__(self.NOTE_OFF, channel, number, velocity)

  def asNoteOn(self):
      return NoteOnMessage(self.channel, self.number, 0)


class NoteOnMessage(NoteMessage):
  def __init__(self, channel=-1, number=-1, velocity=-1):
      super(NoteOnMessage, self).__init__(self.NOTE_ON, channel, number, velocity)


class UnknownMessage(Message):
  def fromBytes(self, bytes):
      super(UnknownMessage, self).fromBytes(bytes)
      self.bytes = bytes[1:]
      return self

  def toBytes(self):
     if not self.bytes:
         raise Exception('Message is not initialised')
     return super(UnknownMessage, self).toBytes()

  def __init__(self, type=-1, channel=-1, bytes=[]):
      super(UnknownMessage, self).__init__(type, channel)
      self.bytes = bytes[1:]

  def __str__(self):
      return "{}, bytes = ({}))".format(super(UnknownMessage, self).__str__(), " ".join(map(hex,self.bytes)))

class ProgramChangeMessage(Message):
  def fromBytes(self, bytes):
      super(ProgramChangeMessage, self).fromBytes(bytes)
      self.program = bytes[1]
      return self

  def toBytes(self):
     if self.program == -1:
         raise Exception('Message is not initialised')
     return super(ProgramChangeMessage, self).toBytes() + [self.program]

  def __init__(self, channel=-1, program=-1):
      super(ProgramChangeMessage, self).__init__(self.PROGRAM_CHANGE, channel)
      self.program = program

  def __str__(self):
      return "{}, program = {})".format(super(ProgramChangeMessage, self).__str__(), self.program)

class ControllerChangeMessage(Message):
  CONTROLLERS = {
    0x00:	'Bank Select',
    0x01:	'Modulation Wheel',
    0x02:	'Breath Contoller',
    0x03:	'Undefined',
    0x04:	'Foot Controller',
    0x05:	'Portamento Time',
    0x06:	'Data Entry MSB',
    0x07:	'Main Volume',
    0x08:	'Balance',
    0x09:	'Undefined',
    0x0A:	'Pan',
    0x0B:	'0Ch',
    0x0C:	'Effect Control 1',
    0x0D:	'Effect Control 2',
    0x10:   'General Purpose Controller 1',
    0x11:   'General Purpose Controller 2',
    0x12:   'General Purpose Controller 3',
    0x13:   'General Purpose Controller 4',
    0x20:	'LSB of Bank Select',
    0x21:	'LSB of Modulation Wheel',
    0x22:	'LSB of Breath Contoller',
    0x23:	'LSB of Undefined',
    0x24:	'LSB of Foot Controller',
    0x25:	'LSB of Portamento Time',
    0x26:	'LSB of Data Entry MSB',
    0x27:	'LSB of Main Volume',
    0x28:	'LSB of Balance',
    0x29:	'LSB of Undefined',
    0x2A:	'LSB of Pan',
    0x2B:	'LSB of 0Ch',
    0x2C:	'LSB of Effect Control 1',
    0x2D:	'LSB of Effect Control 2',
    0x30:	'LSB of General Purpose Controller 1',
    0x31:	'LSB of General Purpose Controller 2',
    0x32:	'LSB of General Purpose Controller 3',
    0x33:	'LSB of General Purpose Controller 4',
    0x40:	'Damper Pedal (Sustain) [Data Byte of 0-63=0ff, 64-127=On]',
    0x41:	'Portamento',
    0x42:	'Sostenuto',
    0x43:	'Soft Pedal',
    0x44:	'Legato Footswitch',
    0x45:	'Hold 2',
    0x46:	'Sound Controller 1 (default: Sound Variation)',
    0x47:	'Sound Controller 2 (default: Timbre/Harmonic Content)',
    0x48:	'Sound Controller 3 (default: Release Time)',
    0x49:	'Sound Controller 4 (default: Attack Time)',
    0x4A:	'Sound Controller 5 (default: Brightness)',
    0x4B:	'Sound Controller 6',
    0x4C:	'Sound Controller 7',
    0x4D:	'Sound Controller 8',
    0x4E:	'Sound Controller 9',
    0x4F:	'Sound Controller 10',
    0x50:	'General Purpose Controller 5',
    0x51:	'General Purpose Controller 6',
    0x52:	'General Purpose Controller 7',
    0x53:	'General Purpose Controller 8',
    0x54:	'Portamento Control',
    0x5B:	'Effects 1 Depth (previously External Effects Depth)',
    0x5C:	'Effects 2 Depth (previously Tremolo Depth)',
    0x5D:	'Effects 3 Depth (previously Chorus Depth)',
    0x5E:	'Effects 4 Depth (previously Detune Depth)',
    0x5F:	'Effects 5 Depth (previously Phaser Depth)',
    0x60:	'Data Increment',
    0x61:	'Data Decrement',
    0x62:	'Non-Registered Parameter Number LSB',
    0x63:	'Non-Registered Parameter Number LSB',
    0x64:	'Registered Parameter Number LSB',
    0x65:	'Registered Parameter Number MSB',
    }

  def fromBytes(self, bytes):
      super(ControllerChangeMessage, self).fromBytes(bytes)
      self.control = bytes[1]
      self.value = bytes[2]
      return self

  def toBytes(self):
     if self.control == -1 or self.value == -1:
         raise Exception('Message is not initialised')
     return super(ControllerChangeMessage, self).toBytes() + [self.control, self.value]

  def __init__(self, channel=-1, control=-1, value=-1):
      super(ControllerChangeMessage, self).__init__(self.CONTROL_CHANGE, channel)
      self.control = control
      self.value = value

  def __str__(self):
      return "{}, control = {}, value = {})".format(super(ControllerChangeMessage, self).__str__(),
               self.CONTROLLERS.get(self.control, 'Unknown Controller ({})'.format(hex(self.control))),
               self.value)

# TODO: other message types
