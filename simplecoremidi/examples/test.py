import os.path
import sys
__dir__ = os.path.dirname(__file__)
sys.path.append(os.path.join(__dir__, '..'))

from simplecoremidi import MIDIDestination, MIDISource, NoteOnMessage, NoteOffMessage
from time import sleep

NOTE_ON = 0x90
channel = 1
MIDDLE_C = 60

for d in MIDIDestination.list():
    print("send message to %s" % d.name)
    d.send(NoteOnMessage(channel, MIDDLE_C, 127))
    sleep(1)
    d.send(NoteOffMessage(channel, MIDDLE_C).asNoteOn())

while (True):
  for s in MIDISource.list():
    message = s.receive(timeout=2)
    if message == None:
      sys.stdout.write('.')
    else:
      print (s.name, str(message))
