import argparse
from simplecoremidi import MIDISource, MIDIDestination, ControllerChangeMessage, ProgramChangeMessage, NoteOffMessage, NoteOnMessage , NoteMessage
from time import sleep, time as now
import sys
import os
import logging
from threading import Timer, Lock

logging.basicConfig(format="%(levelname)-6s %(funcName)-20s   %(msg)s")
logger = logging.getLogger("MIDIMapper")

try:
    import autopy
    from autopy import key
except:
    print >> sys.stderr, ("autopy is not available. Keystroke actions will not work")
    autopy = None
    key = None

DEFAULT_CHANNEL = 15
DEFAULT_DURATION = 0.2
DEFAULT_PORT = None

def typename(obj):
    return type(obj).__name__

class EndpointError(Exception):
    pass

class MIDIMapper(object):
    TRUE = object()
    __pending_responses = {}

    def __init__(self, actions, source, destination):
        self.actions = actions
        self.find_endpoints(source, destination)

    def dequeue_response(self, trigger):
        result = self.__pending_responses.get(trigger, None)
        if result:
            del self.__pending_responses[trigger]
        return result


    def enqueue_response(self, trigger, response):
        assert isinstance(response, Action)
        assert isinstance(trigger, Trigger)
        trigger.owner = self
        self.__pending_responses[trigger] = response

    @classmethod
    def main(cls, actions):
        args, help = cls.argparse()
        if args.print_ports:
            cls.ports()
            return 0

        if args.verbose:
            logger.setLevel(logging.INFO)
        elif args.debug:
            logger.setLevel(logging.DEBUG)

        try:
            mapper = cls(actions, args.source, args.destination)
        except EndpointError as e:
            print >> sys.stderr, (e.message)
            cls.ports()
            return 2

        try:
            mapper.run()
        except KeyboardInterrupt:
            return 0

    def run(self):
        while True:
            message = self.source.receive(timeout=1)
            if message:
                self.handle(message)
            sleep(0.01) # give timer threads a chance to run

    def handle(self, message):
        action = None
        if isinstance(message, NoteMessage):
            action = self.actions.get(Note(message.number))
        elif isinstance(message, ProgramChangeMessage):
            action = self.actions.get(Program(message.program))
        elif isinstance(message, ControllerChangeMessage):
            action = self.actions.get(Controller(message.control))

        if action is None:
            # if it doesn't have an associated action, pass the message through
            self.destination.send(message)
        else:
            self._maybe_execute(action, message)

    def _maybe_execute(self, responses, message):
        if isinstance(responses, dict):
             for trigger, response in responses.items():
                matches = trigger.matches(message)
                if matches is False:
                    continue
                self.enqueue_response(trigger, response)
                if matches is True:
                    self.execute(trigger, message)
        elif isinstance(responses, (set, list, tuple)):
            for r in responses:
                self.enqueue_response(self.TRUE, r)
                self.execute(self.TRUE, message)
        else:
            self.enqueue_response(self.TRUE, responses)
            self.execute(self.TRUE, message)

    def execute(self, trigger, message):
        with Lock():
            response = self.dequeue_response(trigger)
            if response:
                response.update(self.destination, DEFAULT_CHANNEL, message).execute()
            else:
                logger.error("%s has no queued response" % trigger)

    @classmethod
    def argparse(cls):
        parser = argparse.ArgumentParser("Map MIDI input messages to different outputs")
        parser.add_argument("-v", "--verbose", help="Show verbose output", action='store_true')
        parser.add_argument("-d", "--debug", help="Show debugging output", action='store_true')
        parser.add_argument("source", help="A substring of the name of the MIDI port from which messages are read. The first port found matching this substring will be used")
        parser.add_argument("destination", help="A substring of the name of the MIDI port to which messages are written. The first port found matching this substring will be used")
        parser.add_argument("--ports", help="Show the available source and destination ports", action="store_true", dest='print_ports')

        return parser.parse_args(), parser.format_help()

    @classmethod
    def ports(cls):
        print >> sys.stderr, "Available sources:"
        print >> sys.stderr, "    " + "\n    ".join([s.name for s in MIDISource.list()])
        print >> sys.stderr, ""
        print >> sys.stderr, "Available destinations:"
        print >> sys.stderr, "    " + "\n    ".join([d.name for d in MIDIDestination.list()])
        return 1

    def find_endpoints(self, source_substring, destination_substring):
        sources = [s for s in MIDISource.list() if s.name.find(source_substring) != -1]
        if sources:
            self.source = sources[0]
            logger.info("Using \"%s\" as the midi source" % self.source.name)
        else:
            raise EndpointError("Unable to find a source with a substring of %s" % source_substring)

        destinations = [s for s in MIDIDestination.list() if s.name.find(destination_substring) != -1]
        if destinations:
            self.destination = destinations[0]
            logger.info("Using \"%s\" as the midi destination" % self.destination.name)
        else:
            raise EndpointError("Unable to find a destination with a substring of %s" % destination_substring)


class Trigger(object):
    LONG_PRESS_THRESHOLD = 0.5
    LONG_PRESS_ATTR = '__is_longpress__'

    __notes_down = {}

    def _maybe_set_longpress_attr(self, message):
        """
        determines (on note off) whether the note was on for long enough to be a long press.
        This is computed once per note number, and is attached as an attribute to the note off message.

        As such, this method immediately if:
            --  longpress has already been computed (the message contains that attribute)
            --  it is not a note message
            --  it is a not a note off message

        Consequently, the "is_longpress" state of a message can be True, False, or unknown (no attribute)

        """
        def set_note_down(number):
            if number not in self.__notes_down:
                self.__notes_down[number] = now()
                logger.debug ("note %d on at %0.2f (%s)" % (
                    number, self.__notes_down[number], typename(self)))

        if hasattr(message, self.LONG_PRESS_ATTR):
            return

        if not isinstance(message, NoteMessage):
            return

        if not message.is_note_off():
            set_note_down(message.number)
            return

        if message.number not in self.__notes_down:
            return

        duration = (now() - self.__notes_down[message.number])
        if duration > self.LONG_PRESS_THRESHOLD:
            is_long_press = True
        else:
            is_long_press = False

        setattr(message, self.LONG_PRESS_ATTR, is_long_press)
        logger.debug ("note %d off at %0.2f (duration %0.2f): %s (%s)" % (
            message.number, now(), duration,
            "long press" if is_long_press else "tap",
            typename(self)))
        del self.__notes_down[message.number]



class LongPress(Trigger):

    def matches(self, message):
        self._maybe_set_longpress_attr(message)
        return getattr(message, self.LONG_PRESS_ATTR, None) is True


class Tap(Trigger):
    def matches(self, message):
        self._maybe_set_longpress_attr(message)
        return getattr(message, self.LONG_PRESS_ATTR, None) is False

class Action(object):
    def execute(self):
        pass

    def update(self, *args, **kwargs):
        return self


class Keystroke(Action):
    def __init__(self, key, modifiers=0, duration=DEFAULT_DURATION):
        self.key = key
        self.modifiers = modifiers
        self.duration = duration

    def execute(self):
        if autopy:
            logger.debug("Keypress %s" % self.key)
            autopy.key.toggle(self.key, True, self.modifiers)
            sleep(self.duration)
            autopy.key.toggle(self.key, False, self.modifiers)
        else:
            logger.debug("autopy not found")

class MIDIAction(Action):
    def __init__(self, port, channel):
        self.update(port, channel, message=None)

    def update(self, port, channel, message, **kwargs):
        self.port = port
        self.channel = channel
        self.message = message
        return self

class Note(MIDIAction):
    OFF = 0
    ON = 1
    def __init__(self, number, velocity=100, toggle=False, duration=DEFAULT_DURATION, port=DEFAULT_PORT, channel=DEFAULT_CHANNEL):
        super(Note, self).__init__(port, channel)
        self.number = number
        self.velocity = velocity
        self.toggle = toggle
        self.duration = duration

        self.__state = self.OFF

    def __do_toggle(self):
        if self.__state == self.ON:
            self.port.send(NoteOffMessage(channel=self.channel, number=self.number).asNoteOn())
            self.__state = self.OFF
        else:
            self.port.send(NoteOnMessage(channel=self.channel, number=self.number, velocity=self.velocity))
            self.__state = self.ON
        logger.debug("note %d toggled %s" % (self.number, "off" if self.__state == self.OFF else "on"))

    def __do_tap(self):
        self.port.send(NoteOnMessage(channel=self.channel, number=self.number, velocity=self.velocity))
        sleep(self.duration)
        self.port.send(NoteOffMessage(channel=self.channel, number=self.number).asNoteOn())
        logger.debug("note %d tapped for %d seconds" % (self.number, self.duration))

    def execute(self):
        is_note_off = getattr(self.message, 'is_note_off', None)
        if is_note_off and not is_note_off():
            return

        if self.toggle:
            self.__do_toggle()
        else:
            self.__do_tap()

    # FIXME -- need to be smarter about this hashing
    def __hash__(self):
        return hash(self.number)

    def __eq__(self,other):
        return self.number == getattr(other,'number', None)


class Program(MIDIAction):
    def __init__(self, program, port=DEFAULT_PORT, channel=DEFAULT_CHANNEL):
        super(Program, self).__init__(port, channel)
        self.program = program

    def execute(self):
        logger.debug("program %s (ch %s) ", self.program, self.channel)
        self.port.send(ProgramChangeMessage(channel=self.channel, program=self.program))

        # FIXME -- need to be smarter about this hashing
    def __hash__(self):
        return hash(self.program)

    def __eq__(self,other):
        return self.program == other.program


class Controller(MIDIAction):
    def __init__(self, control, value=-1, port=DEFAULT_PORT, channel=DEFAULT_CHANNEL):
        super(Controller, self).__init__(port, channel)
        self.control = control
        self.value = value

    def execute(self):
        logger.debug("program %s = %s (ch %s) ", self.control, self.value, self.channel)
        self.port.send(ControllerChangeMessage(channel=self.channel, control=self.control, value=self.value))

    # FIXME -- need to be smarter about this hashing
    def __hash__(self):
        return hash(self.control)

    def __eq__(self,other):
        return self.control == other.control


class Send(MIDIAction):
    def __init__(self, **kwargs):
        self.message = None
        self.kwargs = kwargs

    def execute(self):
        for attr, value in self.kwargs.items():
            setattr(self.message, attr, value)
        self.port.send(self.message)


class Change(Trigger):
    __last_value = {}

    def __init__(self, attribute='value'):
        self.attribute = attribute

    def matches(self, message):
        last_value = self.__last_value.get(message, None)
        this_value = getattr(message, self.attribute, None)

        self.__last_value[message] = this_value
        return last_value != this_value


class Compare(Trigger):
    def __init__(self, predicate, duration=0):
        self.predicate = predicate
        self.duration = duration
        self.owner = None

        self.timer = None

    def fire(self, *args, **kwargs):
        #_self = args[0]
        _message = args[1]
        logger.debug("%s firing trigger" % self)
        self.timer = None
        self.owner.execute(self, _message)

    def matches(self, message):
        result = self.predicate (message)
        if result:
            if self.duration > 0:
                if not self.timer or not self.timer.is_alive():
                    logger.debug("%s initiated a deferred trigger" % self)
                    self.timer = Timer(self.duration, self.fire, args=(self, message))
                    self.timer.start()
                result = None  # we havent matched yet
        else:
            #logger.debug("%s became false before the duration expired" % self)
            if self.timer:
                self.timer.cancel()

        return result