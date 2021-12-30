#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Component base type classes (including enums)
"""

import asyncio
import datetime
import json
import queue
import threading

from enum import Enum
from datetime import datetime, timedelta

data_types = {
    'bool':     "?",
    'char':     "c",
    'int8':     "b",
    'uint8':    "B",
    'int16':    "h",
    'uint16':    "H",
    'int32':    "i",
    'uint32':   "I",
    'int64':    "q",
    'uint64':   "Q",
    'float':    "f",
    'double':   "d",
    'string':   "s"
}

data_sizes = {
    'bool':     1,
    'char':     1,
    'int8':     1,
    'uint8':    1,
    'int16':    2,
    'uint16':   2,
    'int32':    4,
    'uint32':   4,
    'int64':    8,
    'uint64':   8,
    'float':    4,
    'double':   8,
    'string':   256
}


def dataTypesToFormat(dataTypes):
    """ Convert data schema types to format for use in struct packing/unpacking. """
    format = "<"
    for t in str(dataTypes).split(','):
        if t.startswith('string') & (len(t.split('_')) > 1):
            format += t.split('_')[1] + 's'
        else:
            format += data_types[t]
    return format


def dataTypesToSize(dataTypes):
    """ Convert data schema types to format for use in struct packing/unpacking. """
    size = 0
    for t in str(dataTypes).split(','):
        if t.startswith('string') & (len(t.split('_')) > 1):
            size += int(t.split('_')[1])
        else:
            size += data_sizes[t]
    return size


def timestamp():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


class Status(Enum):
    """ Enum of viable sub-system / component status values """

    UNKNOWN = 0
    OPERATIONAL = 1
    CAUTION = 2
    FAILURE = 3

    @staticmethod
    def to_string(status):
        """ Get string representation of enum name """
        return ''.join(word.title() for word in status.name.split('_'))


class Style:
    """ Enum to hold relevant console output styling tags. """

    # Available formatting tag prefixes
    OK = '\033[2;32m'
    INFO = '\033[2;90m'
    WARNING = '\033[2;33m'
    ERROR = '\033[2;91m'
    MISC = '\033[2;36m'
    # Postfixed tag to indicate where styling ends
    EOS = '\033[0m'


class Protocol(Enum):
    """ Enum of viable sub-system / component status values """

    UNKNOWN = 0
    TCP = 1
    MQTT = 2
    MQTTS = 3

    @staticmethod
    def to_string(protocol):
        """ Get string representation of enum name """
        return protocol.name


class Endpoint:
    """ Basic class containing connection details. """

    def __init__(self, protocol, ip_address, port):
        self.is_active = False
        self.protocol = protocol
        self.ip_address = ip_address
        self.port = port
        self._topics = []

    @property
    def protocol(self):
        """ Connection type [MQTT/MQTTS/TCP]. """
        return self._protocol

    @protocol.setter
    def protocol(self, value):
        if isinstance(value, Protocol):
            self._protocol = value
        else:
            self._protocol = Protocol.MQTT if value == 'MQTT' else Protocol.MQTTS if value == 'MQTTS' else Protocol.TCP if value == 'TCP' else Protocol.UNKNOWN

    @property
    def ip_address(self):
        """ IP address of the connection. """
        return self._ip_address

    @ip_address.setter
    def ip_address(self, value):
        self._ip_address = value

    @property
    def port(self):
        """ Port to use with this connection. """
        return self._port

    @port.setter
    def port(self, value):
        self._port = value

    @property
    def is_active(self):
        """ Indicates if the endpoint is active. """
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        self._is_active = value

    @property
    def topics(self):
        """ [OPTIONAL] List of topics on the source sub-system containing input data, for use by MQTT endpoints. """
        return self._topics


class Component:
    """ [Abstract] Base class of sub-system component classes, do not use directly. """

    def __init__(self):
        if type(self) is Component:  # pylint: disable=unidiomatic-typecheck
            raise Exception(
                "Component is intended as an abstract base class, derive from this class to use.")
        self._status = Status.OPERATIONAL
        self._error_count = 0
        self._is_started = False
        self._is_shutting_down = False
        self._loop_iteration = 0
        self._activity_queue = queue.SimpleQueue()
        self._event_loop = None
        self._worker = None

    @property
    def activity_queue(self):
        """ Activity measurements, subsequently used to determine the throughput rate. """
        return self._activity_queue

    @property
    def is_started(self):
        """
        Execution loop has been started and is currently running, setting to false will terminate the execution
        of logic on the active loop.
        """
        return self._is_started

    @property
    def loop_iteration(self):
        """ Current looping sequence, incremented on starting/stopping the execution loop. """
        return self._loop_iteration

    @property
    def error_count(self):
        """ Active count of error events encountered in the component. """
        return self._error_count

    @property
    def status(self):
        """ Current component status, aggregated into a wider sub-system status. """
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    async def increment_error_count(self):
        """ Increment the session error count. """
        self._error_count += 1

    async def start_async(self):
        """ Asynchronously sets the flag that governs ongoing execution loops and creates a new worker thread. """
        self._loop_iteration += 1
        self._is_started = False
        if self._worker and self._worker.is_alive():
            self._worker.join(2)
        self._is_started = True
        self._worker = threading.Thread(target=self.loop_process, daemon=True)
        self._worker.start()

    async def stop_async(self):
        """ Asynchronously sets the flag that terminates any ongoing execution loops and joins the worker thread back. """
        self._is_started = False
        self._loop_iteration += 1
        if self._worker:
            self._worker.join(2)
        self._worker = threading.Thread(target=asyncio.run, args=(
            self.purge_loop_async(),), daemon=True)
        self._worker.start()

    def halt(self):
        """ Sets the flags/counters used to terminate any ongoing execution loops. """
        self._is_started = False
        self._loop_iteration += 1

    async def shutdown_async(self):
        """ Attempts to terminate any ongoing logic execution, allowing for the release of the process. """
        self._is_shutting_down = True
        await self.stop_async()
        self._loop_iteration += 1
        if self._worker and self._worker.is_alive():
            self._worker.join(2)

    def loop_process(self):
        """ Managed running of the execution loop, initializing a new loop for the run. """
        try:
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
            self._event_loop.run_until_complete(self.loop_async())
        except Exception as x:
            self._event_loop.stop()
            print(f"{Style.ERROR}encountered issue, event loop forcefully terminated with:\n -> \"{x}\"{Style.EOS}", flush=True)

    async def loop_async(self):
        """ [Abstract] Primary loop of the component, controlled by the start and stop methods. """
        if type(self) is Component:  # pylint: disable=unidiomatic-typecheck
            raise Exception(
                "Derived classes must override the loop() function.")

    async def purge_loop_async(self):
        """ Makes sure that the queues remain empty where not started, controlled by the stop and start methods. """
        if type(self) is Component:  # pylint: disable=unidiomatic-typecheck
            raise Exception(
                "Derived classes must override the purge_loop_async() function.")


class DataItem:
    """
    [Abstract] Base class of data types, do not use directly.\n
    The class allows for interaction with the descriptive model of a pre-configured data stream.\n
    """

    def __init__(self, data_config):
        self._key = data_config['key']
        self._config = data_config
        self._forced_refresh_time = datetime.max

    @property
    def key(self):
        """ Unique key used to identify the instantiated data item. """
        return self._key

    def reset_force_refresh_time(self):
        """
        Resets the initialization time on the data item, for use by a subsequent check that verifies correct
        initialization of the data item from configuration.
        """
        self._forced_refresh_time = datetime.now() + timedelta(seconds=2)

    def needs_initialization(self):
        """ Data item undefined on broker, needs to be initialization from config defaults """
        return datetime.now() >= self._forced_refresh_time

    def from_input(self, payload):
        """ Update instance from message payload """
        if payload and (json.loads(payload) == self._config):
            self._forced_refresh_time = datetime.max
        else:
            self.reset_force_refresh_time()

    def to_output(self):
        """ Get unmapped format for message payload from current instance """
        return json.dumps(self._config)


class Observer():
    """
    Enables use of the observer pattern of events by self-registration for event consumption.
    Derived:
        Answer by user Pithikos (https://stackoverflow.com/users/474563/pithikos) on
        StackOverflow (https://stackoverflow.com/questions/1092531/event-system-in-python)
    """

    _observers = []

    def __init__(self):
        self._observers.append(self)
        self._observed_events = []

    def observe(self, event_name, callback_fn):
        self._observed_events.append(
            {'event_name': event_name, 'callback_fn': callback_fn})


class Event():
    """
    Allows for raising an event as registered, with optional event arguments.
    Derived:
        Answer by user Pithikos (https://stackoverflow.com/users/474563/pithikos) on
        StackOverflow (https://stackoverflow.com/questions/1092531/event-system-in-python)
    """

    def __init__(self, event_name, *callback_args):
        for observer in Observer._observers:
            for observable in observer._observed_events:
                if observable['event_name'] == event_name:
                    if callback_args:
                        observable['callback_fn'](*callback_args)
                    else:
                        observable['callback_fn']()


class Control(Observer):
    """ [Abstract] Base class of control types, do not use directly. """

    def __init__(self, control_config):
        if type(self) is Control:  # pylint: disable=unidiomatic-typecheck
            raise Exception(
                "Control is intended as an abstract base class, derive from this class to use.")
        super().__init__()
        self.uid = str.replace(control_config['uid'], '-', '')
        self._type = control_config['type']
        self._label = control_config['label']
        self._forced_refresh_time = datetime.max

    def observe(self, event_name, callback_fn):
        self._observed_events.append(
            {'event_name': event_name, 'callback_fn': callback_fn})

    def reset_force_refresh_time(self):
        """
        Resets the initialization time on the control, for use by a subsequent check that verifies correct
        initialization of the control from configuration.
        """
        self._forced_refresh_time = datetime.now() + timedelta(seconds=2)

    def needs_initialization(self):
        """ Control undefined on broker, needs to be initialization from config defaults """
        return datetime.now() >= self._forced_refresh_time

    def decode(self, payload):
        """ Decode message from json input and return result, None if empty """
        decoded_string = str(payload.decode('utf-8'))
        if not decoded_string:
            return None

        json_map = json.loads(decoded_string)
        if json_map['type'] != self._type:
            return None

        self._forced_refresh_time = datetime.max
        return json_map

    def from_input(self, payload):
        """ Update instance from message payload """
        raise NotImplementedError(
            'Derived classes must override the from_input() function.')

    def to_output(self):
        """ Get unmapped format for message payload from current instance """
        raise NotImplementedError(
            'Derived classes must override the to_output() function.')
