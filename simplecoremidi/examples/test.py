import os.path
import sys
__dir__ = os.path.dirname(__file__)
sys.path.append(os.path.join(__dir__, '..'))

from time import sleep
import simplecoremidi

root_note = 60  # This is middle C
channel = 1  # This is MIDI channel 1
note_on_action = 0x90
major_steps = [2, 2, 1, 2, 2, 2, 1, 0]
velocity = 127

"""
for d in simplecoremidi.MIDIDestination.list():
    print("send scale to %s" % d.name)

    note = root_note
    for step in major_steps:
        d.send((note_on_action | channel,
                   note,
                   velocity))
        sleep(0.1)
        d.send((note_on_action | channel,
                   note,
                   0))  # A note-off is just a note-on with velocity 0

        note += step
        sleep(0.2)

"""

def printBytes(bytes):
  print(bytes)

sources = simplecoremidi.MIDISource.list()
for s in sources:
  print(s.name)
  s.receive(printBytes)

while (True):
  sleep(1)
