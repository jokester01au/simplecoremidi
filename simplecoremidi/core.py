from . import _simplecoremidi as cfuncs

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

  def receive(self):
        return cfuncs.recv_midi(self._source())

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

  def send(self, midi_data):
        assert isinstance(midi_data, tuple) or isinstance(midi_data, list)
        return cfuncs.send_midi(self._destination(), midi_data)

  @classmethod
  def list(cls):
      return [MIDIDestination( cfuncs.get_midi_endpoint_name(i), i)
           for i in cfuncs.get_midi_destination_list()
      ]

