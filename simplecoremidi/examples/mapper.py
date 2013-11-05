from simplecoremidi import NoteOffMessage, NoteOnMessage, MIDISource, MIDIDestination
import time
import sys
import os


class MidiMapper(object):
    LONG_PRESS_THRESHOLD_MS = 1000
    TOGGLE_VELOCITY = 100

    __NOTE_ON = 1
    __NOTE_OFF = 0

    def __init__(self):
        self.notes_down = {}
        self.output_state = {}

    def is_long_press(self, message):
        result = False
        if isinstance(message, NoteOnMessage):
            self.notes_down[message.note] = time.clock()
        elif isinstance(message, NoteOffMessage):
            if message.note in self.notes_down:
                if (time.clock() - self.notes_down[message.note]) > self.LONG_PRESS_THRESHOLD_MS:
                    result = True
                del self.notes_down[message.note]
        return result

    def keystroke(self, keystroke):
        try:
            sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__))))
            from autopy import key
        except:
            print("\n".join(sys.path))
            raise Exception('autopy is not available')
