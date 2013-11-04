# simplecoremidi

A fork of the [simplecoremidi](https://pypi.python.org/pypi/simplecoremidi) python package that 
      - is object oriented
      - allows you to directly send and receive data to/from external devices.
      - blocks (with a timeout) for MIDISource.receive rather than requiring you to poll

**NOTE: As it says in the title, this is a wrapper around the OS X CoreMIDI framework. Don't expect this to work in any other OS.**
### Installation

  sudo python install setup.py
  
### Usage
```python
  from simplecoremidi import MIDIDestination, MIDISource
  from time import sleep
  
  NOTE_ON = 0x90
  channel = 1
  MIDDLE_C = 60
  
  for d in MIDIDestination.list():
      print("send middle-c to %s" % d.name)
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
```
### TODO


  - Unbreak the original functionality that allowed you to create virtual endpoints
  - "hijack" ports to prevent messages from being propagated to other endpoints
