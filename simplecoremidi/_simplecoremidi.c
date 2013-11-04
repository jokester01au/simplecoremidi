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
  void *callback;
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
SCMConnectExternalSource(MIDIEndpointRef ref, void *callback) {
    OSStatus result;
  SCMExternalSourceRef sourceRef
    = CFAllocatorAllocate(NULL, sizeof(struct _SCMExternalSource), 0);
  sourceRef->receivedMidi = CFDataCreateMutable(NULL, 0);
  sourceRef->source = ref;
  sourceRef->port = nil;
  sourceRef->callback = callback;

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
  PyObject *callback;
  PyObject *pyEndpoint;

  if (!PyArg_UnpackTuple(args, "OO:get_source", 2, 2, &pyEndpoint, &callback))
  {
      printf("failed to parse\n");
      PyErr_SetString(PyExc_TypeError, "failed to parse arguments");
      return NULL;
  }
  Py_XINCREF(callback);         /* Add a reference to new callback */

  if (!PyCallable_Check(callback)) {
      printf("not callable\n");
      PyErr_SetString(PyExc_TypeError, "parameter must be callable");
      return NULL;
  }
  endpoint = PyCObject_AsVoidPtr(pyEndpoint);
  sourceRef = SCMConnectExternalSource(endpoint, callback);

  PyObject_Call(sourceRef->callback, PyTuple_New(0), PyDict_New());
  return PyCObject_FromVoidPtr(sourceRef, SCMExternalSourceDispose);
}

static PyObject*
SCMGetDestinationPyObject(PyObject* self, PyObject* args) {
  SCMExternalSourceRef destRef;
  MIDIEndpointRef endpoint;
  PyObject *pyEndpoint;

  if (!PyArg_ParseTuple(args, "O", &pyEndpoint))
  {
      PyErr_SetString(PyExc_TypeError, "failed to parse arguments");
      return NULL;
  }
  endpoint = PyCObject_AsVoidPtr(pyEndpoint);

  destRef = SCMConnectExternalDestination(endpoint);
  if (destRef == nil)
  {
      PyErr_SetString(PyExc_TypeError, "Failed to connect external destination");
      return NULL;
  }
  return PyCObject_FromVoidPtr(destRef, SCMExternalDestinationDispose);
}

static PyObject *
SCMGetMidiEndpointName(PyObject* self, PyObject* args) {
  PyObject *result;
  CFStringRef name = nil;
  PyObject *pyEndpoint;

  PyArg_ParseTuple(args, "O", &pyEndpoint);

  if (noErr != MIDIObjectGetStringProperty(PyCObject_AsVoidPtr(pyEndpoint), kMIDIPropertyDisplayName, &name)) {
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
      PyObject * midiSource = PyCObject_FromVoidPtr(MIDIGetSource(i), NULL);
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
      PyObject * midiDestination = PyCObject_FromVoidPtr(MIDIGetDestination(i), NULL);
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
      PyErr_SetString(PyExc_TypeError, "failed to create the midi packet");

  result = MIDISend(destRef->port, destRef->destination, pktList);
  if (noErr != result)
      PyErr_SetString(PyExc_TypeError, "failed to send the packet");

  Py_INCREF(Py_None);
  return Py_None;
}


void
SCMRecvMIDIPyCallback(SCMExternalSourceRef sourceRef) {
  PyObject* receivedMidiT;
  UInt8* bytePtr;
  int i;
  CFIndex numBytes;
  PyObject *arglist;

  numBytes = CFDataGetLength(sourceRef->receivedMidi);

  receivedMidiT = PyTuple_New(numBytes);
  bytePtr = CFDataGetMutableBytePtr(sourceRef->receivedMidi);
  for (i = 0; i < numBytes; i++, bytePtr++) {
    PyObject* midiByte = PyInt_FromLong(*bytePtr);
    PyTuple_SetItem(receivedMidiT, i, midiByte);
  }

  arglist = Py_BuildValue("(O)", receivedMidiT);
  PyObject_CallObject((PyObject *)sourceRef->callback, arglist);
  Py_DECREF(arglist);
  Py_DECREF(receivedMidiT);
  CFDataDeleteBytes(sourceRef->receivedMidi, CFRangeMake(0, numBytes));
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
  SCMRecvMIDIPyCallback(sourceRef);

}



static PyMethodDef SimpleCoreMidiMethods[] = {
  {"get_midi_endpoint_name", SCMGetMidiEndpointName, METH_VARARGS, "Get the name of a midi endpoint."},
  {"get_midi_source_list", SCMGetSourceListPyObject, METH_NOARGS, "Get the available MIDI sources."},
  {"get_midi_source", SCMGetSourcePyObject, METH_VARARGS, "Get a MIDI destination object."},
  {"get_midi_destination", SCMGetDestinationPyObject, METH_VARARGS, "Get a MIDI destination object."},
  {"get_midi_destination_list", SCMGetDestinationListPyObject, METH_NOARGS, "Get the available MIDI destinations."},
  {"send_midi", SCMSendMidi, METH_VARARGS, "Send midi data tuple to an external destination."},
  {NULL, NULL, 0, NULL}
};


PyMODINIT_FUNC
init_simplecoremidi(void) {
  (void) Py_InitModule("_simplecoremidi", SimpleCoreMidiMethods);
}
