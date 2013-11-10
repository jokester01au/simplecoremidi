import mapper
import time
from simplecoremidi import MIDISource, MIDIDestination
from mapper import Note, Tap, LongPress, Controller, Program, MIDIMapper, Keystroke, key, Change, Send, Compare, typename
import sys
import os

# TODO: parse from a file
ACTIONS = {
    Note(1): { LongPress(): Keystroke(key.K_F16), Tap(): Keystroke(key.K_F17) },
    Note(6): { LongPress(): Keystroke(key.K_F18), Tap(): Keystroke(key.K_F19) },

    Note(2): { Tap(): Note(2), LongPress(): Note(12) },
    Note(7): { Tap(): Note(7, toggle=True), LongPress(): Note(17) },

    Note(3): { Tap(): Note(3, toggle=True), LongPress(): Note(13, toggle=True) },
    Note(4): { Tap(): Note(4, toggle=True), LongPress(): Note(14, toggle=True) },
    Note(5): { Tap(): Note(5, toggle=True), LongPress(): Note(15, toggle=True) },
    Note(8): { Tap(): Note(8, toggle=True), LongPress(): Note(18, toggle=True) },
    Note(9): { Tap(): Note(9, toggle=True), LongPress(): Note(19, toggle=True) },
    Note(10):{ Tap(): Note(10,toggle=True), LongPress(): Note(20, toggle=True) },

    #Note(8):  { Tap(): Program(8),  LongPress(): Program(18)},
    #Note(9):  { Tap(): Program(9),  LongPress(): Program(19)},
    #Note(10): { Tap(): Program(10), LongPress(): Program(20)},

    Controller(0x1A): {},
    Controller(0x1B): { Change(): Send(control=0x0C) },
    Controller(12): { Change(): Send(), Compare(lambda m: m.value > 120, duration=1.0): Note(11, toggle=True)},
}

if __name__ == '__main__':
    sys.exit(MIDIMapper.main(ACTIONS))

