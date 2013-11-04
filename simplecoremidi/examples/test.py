import os.path
import sys
__dir__ = os.path.dirname(__file__)
sys.path.append(os.path.join(__dir__, '..'))

from simplecoremidi import MIDIDestination, MIDISource
from time import sleep

NOTE_ON = 0x90
channel = 1
MIDDLE_C = 60

for d in MIDIDestination.list():
    print("send message to %s" % d.name)
    d.send((NOTE_ON | channel, MIDDLE_C, 127))
    sleep(1)
    d.send((NOTE_ON | channel, MIDDLE_C, 0))

while (True):
  for s in MIDISource.list():
    bytes = s.receive(timeout=2)
    if bytes == None:
      print ('%s timed out' % s.name)
    else:
      print (s.name, map(hex, bytes))
