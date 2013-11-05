import mapper
import autopy
from simplecoremidi import MIDISource, MIDIDestination, ControllerChangeMessage, ProgramChangeMessage, NoteOffMessage, NoteOnMessage 


# TODO: generalise the action source
ACTIONS = {
    1: { LongPress(): Keystroke(key.K_F16), Tap(): Keystroke(key.K_F17) },
    6: { LongPress(): Keystroke(key.K_F18), Tap(): Keystroke(key.K_F19) },
    
    2: { Tap(): Note(note=2), LongPress(): Note(note=12) },
    7: { Tap(): Note(note=7), LongPress(): Note(note=17) },
    
    3: { Tap(): Note(toggle=True, note=3), LongPress(): Note(toggle=True, note=13) },
    4: { Tap(): Note(toggle=True, note=4), LongPress(): Note(toggle=True, note=14) },
    5: { Tap(): Note(toggle=True, note=5), LongPress(): Note(toggle=True, note=15) },
    
    8:  { Tap(): Program(number=8),  LongPress(): Program(number=18)},
    9:  { Tap(): Program(number=9),  LongPress(): Program(number=19)},
    10: { Tap(): Program(number=10), LongPress(): Program(number=20)},
}

DEFAULT_CHANNEL = 16
DEFAULT_DURATION = 1
DEFAULT_PORT = None

class Trigger(object):
    pass

class LongPress(Trigger):
    def __init__(self, duration=DEFAULT_DURATION):
        self.duration = duration

class Tap(Trigger):
    pass

class Action(object):
    def execute(self):
        pass

class Keystroke(Action):
    def __init__(self, key, modifiers=None, duration=DEFAULT_DURATION):
        self.key = key
        self.modifiers = modifiers
        self.duration = duration

    def execute(self):
        autopy.key.toggle(self.key, True, self.modifiers)
        time.sleep(self.duration)
        autopy.key.toggle(self.key, False, self.modifiers)


class Note(Action):
    OFF = 0
    ON = 1
    def __init__(self, number, velocity=100, toggle=False, duration=DEFAULT_DURATION, port=DEFAULT_PORT, channel=DEFAULT_CHANNEL):
        self.number = number
        self.velocity = velocity
        self.toggle = toggle
        self.duration = duration
        self.port = port

        self.__state = self.OFF

    def __do_toggle(self):
        if self.__state == self.ON:
            self.port.send(NoteOffMessage(channel=self.channel, number=self.number).asNoteOn())
            self.__state = self.OFF
        else:
            self.port.send(NoteOnMessage(channel=self.channel, number=self.number, velocity=self.velocity))
            self.__state = self.ON

    def __do_tap(self):
        self.port.send(NoteOnMessage(channel=self.channel, number=self.number, velocity=self.velocity))
        time.sleep(self.duration)
        self.port.send(NoteOffMessage(channel=self.channel, number=self.number).asNoteOn())

    def toggle_state(self, message):
        if isinstance(message, NoteOffMessage):
            if self.output_state.get(message.note, self.__NOTE_OFF) == self.__NOTE_OFF:
                self.output_state[message.note] = self.__NOTE_ON
                return NoteOnMessage(message.channel, message.note, self.TOGGLE_VELOCITY)
            else:
                self.output_state[message.note] = self.__NOTE_OFF
                return NoteOffMessage(message.channel, message.note)

    def execute(self):
        if self.toggle:
            self.__do_toggle()
        else:
            self.__do_tap()


class Program(Action):
    def __init__(self, program, port=DEFAULT_PORT, channel=DEFAULT_CHANNEL):
        self.program = program
        self.port = port
        self.channel = channel

    def execute(self):
        self.port.send(ProgramChangeMessage(channel=self.channel, program=self.program))

class Controller(Action):
    def __init__(self, control, value, port=DEFAULT_PORT, channel=DEFAULT_CHANNEL):
        self.control = control
        self.value = value

    def execute(self):
        self.port.send(ControllerChangeMessage(channel=self.channel, control=self.control, value=self.value))



NOTES_TO_TOGGLE = [ 2, 3, 4, 5 ]
NOTES_TO_

if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__))))
    from autopy import key
    MidiMapper().keystroke(key.K_F19)

"""
property NOTES_TO_TOGGLE : {2, 3, 4, 5}
property NOTES_TO_Program : {6, 7, 8, 9, 10}
property NOTES_TO_KEYS : {}
property KEYS_FOR_NOTES : {"Space", "PageUp", "Return", "PageDown"}

property currentState : {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}

property onTime : {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}

-- detect if key held down for longer than 1 second
on isLongPress(message)
  set now to (current date)
  set noteNumber to getMessageNumber(message)
  set messageType to getMessageType(message)
  if messageType = NOTE_ON then
    setItem(onTime, noteNumber, now)
  else if messageType = NOTE_OFF then
    set noteOn to getItem(onTime, noteNumber)
    if (current date) - noteOn > 0 then
      return true
    end if
  end if
  return false
end isLongPress

-- send alternate "note on" / "note off" messages each time the function is called
on toggleNote(message)
  set noteNumber to getMessageNumber(message)
  if getItem(currentState, noteNumber) = 0 then
    setItem(currentState, noteNumber, 1)
    setMessageType(message, NOTE_ON)
  else
    setItem(currentState, noteNumber, 0)
  end if
end toggleNote

-- send a keystroke
on sendKey(noteNumber)
  set currenTap()p to (path to frontmost application)
  tell application "System Events"
    tell process currenTap()p
      keystroke item indexOf(noteNumber, NOTES_TO_KEYS) of KEYS_FOR_NOTES
    end tell
  end tell
end sendKey

on runme(message)
  set messageType to getMessageType(message)
  set messageNumber to getMessageNumber(message)

  if isLongPress(message) then
    setMessageType(message, NOTE_ON)
    setMessageNumber(message, messageNumber + 20)
    return message
  else if messageType = NOTE_OFF then
    if messageNumber is in NOTES_TO_TOGGLE then
      toggleNote(message)
    else if messageNumber is in NOTES_TO_Program then
      setMessageType(message, PROGRAM_CHANGE)
      set message to items 1 thru 2 of message
    else if messageNumber is in NOTES_TO_KEYS then
      sendKey(noteNumber)
    end if
    return message
  else if messageType = NOTE_ON then
    -- swallow it
  else if messageType = CONTROL_CHANGE then
    return message
  end if
end runme
"""
