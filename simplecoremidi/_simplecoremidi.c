#include <pthread.h>
#include <mach/mach_time.h>
#include <CoreMIDI/CoreMIDI.h>
#include <CoreFoundation/CoreFoundation.h>
#include <Python.h>
#include <stdbool.h>
#include <string.h>

struct _SCMExternalSource {
  MIDIEndpointRef source;
  CFMutableDataRef receivedMidi;
  MIDIPortRef port;
};

struct _SCMExternalDestination {
  MIDIEndpointRef destination;
  MIDIPortRef port;
};

typedef struct _SCMExternalSource* SCMExternalSourceRef;
typedef struct _SCMExternalDestination* SCMExternalDestinationRef;


static MIDIClientRef _midiClient;


void
SCMRecvMIDIProc(const MIDIPacketList* pktList,
                void* readProcRefCon,
                void* srcConnRefCon);


static MIDIClientRef
SCMGlobalMIDIClient() {
  if (! _midiClient) {
    MIDIClientCreate(CFSTR("simple core midi client"), NULL, NULL,
                     &(_midiClient));
  }
  return _midiClient;
}

static void
SCMExternalSourceDispose(SCMExternalSourceRef sourceRef) {
    if (sourceRef->port)
        MIDIPortDispose(sourceRef->port);
  CFRelease(sourceRef->receivedMidi);
  CFAllocatorDeallocate(NULL, sourceRef);
}

static void
SCMExternalDestinationDispose(SCMExternalSourceRef destRef) {
    if (destRef->port)
        MIDIPortDispose(destRef->port);
  CFAllocatorDeallocate(NULL, destRef);
}


static SCMExternalSourceRef
SCMConnectExternalSource(MIDIEndpointRef ref) {
    OSStatus result;
  SCMExternalSourceRef sourceRef
    = CFAllocatorAllocate(NULL, sizeof(struct _SCMExternalSource), 0);
  sourceRef->receivedMidi = CFDataCreateMutable(NULL, 0);
  sourceRef->source = ref;
  sourceRef->port = nil;

  result = MIDIInputPortCreate(SCMGlobalMIDIClient(),
                      CFSTR("In"),
                      SCMRecvMIDIProc,
                      sourceRef,
                      &sourceRef->port
                      );
  if (result != noErr)
  {
      SCMExternalSourceDispose(sourceRef);
      return nil;
  }

  result = MIDIPortConnectSource(sourceRef->port, sourceRef->source, sourceRef);
  if (result != noErr)
  {
      SCMExternalSourceDispose(sourceRef);
      return nil;
  }

  return sourceRef;
}

static SCMExternalDestinationRef
SCMConnectExternalDestination(MIDIEndpointRef ref) {
    OSStatus result;
    SCMExternalDestinationRef destRef
      = CFAllocatorAllocate(NULL, sizeof(struct _SCMExternalDestination), 0);

    destRef->destination = ref;

  result = MIDIOutputPortCreate(SCMGlobalMIDIClient(),
                      CFSTR("Out"),
                      &destRef->port
                      );
  if (result != noErr)
  {
      printf("Failed to create output port. %d\n", result);
      SCMExternalDestinationDispose(destRef);
      return nil;
  }

  return destRef;
}

/* =========================== Python Wrappers ===================== */

static PyObject *
SCMGetSourcePyObject(PyObject* self, PyObject* args) {
  MIDIEndpointRef endpoint;
  SCMExternalSourceRef sourceRef;

  PyArg_ParseTuple(args, "i", &endpoint);
  sourceRef = SCMConnectExternalSource(endpoint);

  return PyCObject_FromVoidPtr(sourceRef, SCMExternalSourceDispose);
}

static PyObject*
SCMGetDestinationPyObject(PyObject* self, PyObject* args) {
  SCMExternalSourceRef destRef;
  MIDIEndpointRef endpoint;

  PyArg_ParseTuple(args, "i", &endpoint);

  destRef = SCMConnectExternalDestination(endpoint);
  if (destRef == nil)
  {
      Py_INCREF(Py_None);
      return Py_None;
  }
  return PyCObject_FromVoidPtr(destRef, SCMExternalDestinationDispose);
}

static PyObject *
SCMGetMidiEndpointName(PyObject* self, PyObject* args) {
  PyObject *result;
  CFStringRef name = nil;
  MIDIEndpointRef ref;

  PyArg_ParseTuple(args, "i", &ref);

  if (noErr != MIDIObjectGetStringProperty(ref, kMIDIPropertyDisplayName, &name)) {
      Py_INCREF(Py_None);
      return Py_None;
  }
  result = PyString_FromString(CFStringGetCStringPtr(name, kCFStringEncodingASCII));
  CFRelease(name);
  return result;
}


static PyObject *
SCMGetSourceListPyObject(PyObject* self, PyObject* args) {
  PyObject * midiSources = PyTuple_New(MIDIGetNumberOfSources());

  int i;

  for (i=0; i<MIDIGetNumberOfSources(); i++)
  {
      PyObject * midiSource = PyLong_FromLong(MIDIGetSource(i));
      PyTuple_SetItem(midiSources, i, midiSource);
  }
  return  midiSources;
}

static PyObject *
SCMGetDestinationListPyObject(PyObject* self, PyObject* args) {
  PyObject * midiDestinations = PyTuple_New(MIDIGetNumberOfDestinations());
  int i;

  for (i=0; i<MIDIGetNumberOfDestinations(); i++)
  {
      PyObject * midiDestination = PyLong_FromLong(MIDIGetDestination(i));
      PyTuple_SetItem(midiDestinations, i, midiDestination);
  }
  return  midiDestinations;
}


/* =========================== SEND/RECEIVE functions ===================== */

static PyObject*
SCMSendMidi(PyObject* self, PyObject* args) {
  OSStatus result;
  SCMExternalDestinationRef destRef;
  PyObject* midiData;
  Py_ssize_t nBytes;
  char pktListBuf[1024+100];
  MIDIPacketList* pktList = (MIDIPacketList*) pktListBuf;
  MIDIPacket* pkt;
  Byte midiDataToSend[1024];
  UInt64 now;
  int i;

  destRef = (SCMExternalDestinationRef*) PyCObject_AsVoidPtr(PyTuple_GetItem(args, 0));
  midiData = PyTuple_GetItem(args, 1);
  nBytes = PySequence_Size(midiData);

  for (i = 0; i < nBytes; i++) {
    PyObject* midiByte;

    midiByte = PySequence_GetItem(midiData, i);
    midiDataToSend[i] = PyInt_AsLong(midiByte);
  }

  now = mach_absolute_time();
  pkt = MIDIPacketListInit(pktList);
  pkt = MIDIPacketListAdd(pktList, 1024+100, pkt, now, nBytes, midiDataToSend);

  if (pkt == NULL)
    printf("failed to create the midi packet.\n");

  result = MIDISend(destRef->port, destRef->destination, pktList);
  if (noErr != result)
      printf("failed to send the midi.\n");

  Py_INCREF(Py_None);
  return Py_None;
}


static PyObject*
SCMRecvMidi(PyObject* self, PyObject* args) {
  PyObject* receivedMidiT;
  UInt8* bytePtr;
  int i;
  CFIndex numBytes;
  SCMExternalSourceRef sourceRef
    = (SCMExternalSourceRef) PyCObject_AsVoidPtr(PyTuple_GetItem(args, 0));

  numBytes = CFDataGetLength(sourceRef->receivedMidi);

  receivedMidiT = PyTuple_New(numBytes);
  bytePtr = CFDataGetMutableBytePtr(sourceRef->receivedMidi);
  for (i = 0; i < numBytes; i++, bytePtr++) {
    PyObject* midiByte = PyInt_FromLong(*bytePtr);
    PyTuple_SetItem(receivedMidiT, i, midiByte);
  }

  // fixme --lock or use message queue
  CFDataDeleteBytes(sourceRef->receivedMidi, CFRangeMake(0, numBytes));
  return receivedMidiT;
}


void
SCMRecvMIDIProc(const MIDIPacketList* pktList,
                void* readProcRefCon,
                void* srcConnRefCon) {
  SCMExternalSourceRef sourceRef = (SCMExternalSourceRef) readProcRefCon;
  int i;
  const MIDIPacket* pkt;

  pkt = &pktList->packet[0];
  for (i = 0; i < pktList->numPackets; i++) {
    CFDataAppendBytes(sourceRef->receivedMidi, pkt->data, pkt->length);
    pkt = MIDIPacketNext(pkt);
  }
}

/* FIXME FIXME FIXME -- use receive callback instead of polling: http://stackoverflow.com/questions/6412828/python-wrapper-to-a-c-callback */


static PyMethodDef SimpleCoreMidiMethods[] = {
  {"get_midi_endpoint_name", SCMGetMidiEndpointName, METH_VARARGS, "Get the name of a midi endpoint."},
  {"get_midi_source_list", SCMGetSourceListPyObject, METH_NOARGS, "Get the available MIDI sources."},
  {"get_midi_source", SCMGetSourcePyObject, METH_VARARGS, "Get a MIDI destination object."},
  {"get_midi_destination", SCMGetDestinationPyObject, METH_VARARGS, "Get a MIDI destination object."},
  {"get_midi_destination_list", SCMGetDestinationListPyObject, METH_NOARGS, "Get the available MIDI destinations."},
  {"send_midi", SCMSendMidi, METH_VARARGS, "Send midi data tuple to an external destination."},
  {"recv_midi", SCMRecvMidi, METH_VARARGS, "Receive midi data bytes from an external source."},
  {NULL, NULL, 0, NULL}
};


PyMODINIT_FUNC
init_simplecoremidi(void) {
  (void) Py_InitModule("_simplecoremidi", SimpleCoreMidiMethods);
}
