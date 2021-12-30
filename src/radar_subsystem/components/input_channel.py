#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Input channel component type classes and functionality
"""

import asyncio
import csv
import queue
import ssl
import struct

import paho.mqtt.client as mqtt

from .. import base

READ_INTERVAL = 0.10
CANCELLATION_CHECK_INTERVAL = 0.1
RECHECK_DATA_IN_QUEUE_INTERVAL = 0.05
FORCED_QUEUE_CLEANUP_INTERVAL = 0.5


def on_connect(client, channel, flags, result):
    """ The callback for CONNACK response from MQTT input server, where applicable. """
    print(f"{base.Style.OK}MQTT subscriber connected{base.Style.EOS}")
    for topic in channel.endpoint.topics:
        client.subscribe(topic)
    channel.endpoint.is_active = True
    client.is_connected = True


def on_disconnect(client, channel, result):
    """ The callback for DISCONNECT response from the server, where applicable. """
    if not result:
        print(f"{base.Style.WARNING}MQTT subscriber disconnected{base.Style.EOS}")
    else:
        print(
            f"{base.Style.ERROR}MQTT subscriber unexpectedly terminated{base.Style.EOS}")
    client.user_data_set("")
    channel.endpoint.is_active = False
    client.is_connected = False


def on_message(_, channel, msg):
    """ The callback for PUBLISH message from the server, where applicable. """
    lines = msg.payload.decode('utf-8').splitlines()
    channel.activity_queue.put(len(lines))
    for row in csv.reader(lines):
        channel.queue.put(row)


class CustomProtocol(asyncio.Protocol):
    """ Class containing the relevant handlers for async TCP data sink. """

    def __init__(self, endpoint, queue, activity_queue):
        self._endpoint = endpoint
        self._queue = queue
        self._activity_queue = activity_queue

    def connection_made(self, transport):
        peer = transport.get_extra_info('peername')
        print(
            f"{base.Style.OK}TCP data sink connection opened on {peer[0]}:{peer[1]}{base.Style.EOS}")
        self._endpoint.is_active = True
        self.transport = transport

    def connection_lost(self, transport):
        print(f"{base.Style.WARNING}TCP data sink disconnected{base.Style.EOS}")
        self._endpoint.is_active = False

    def data_received(self, data):
        self._activity_queue.put(1)
        self._queue.put(data)


class InputChannel(base.Component):
    """ Class defining the input channel component, not used with the Control and DataFeeder sub-system types. """

    def __init__(self, local_uid):
        super().__init__()
        self._local_uid = local_uid
        self._endpoint = None
        self._stream_key = None
        self._queue = queue.SimpleQueue()
        self._struct_format = None
        self._struct_size = 0

    @property
    def endpoint(self):
        """ Outgoing connection details. """
        return self._endpoint

    @endpoint.setter
    def endpoint(self, value):
        self._endpoint = value

    @property
    def stream_key(self):
        """ Key name of the active stream. """
        return self._stream_key

    @stream_key.setter
    def stream_key(self, value):
        self._stream_key = value

    @property
    def struct_size(self):
        """ Struct size of individual data packet. """
        return self._struct_size

    @struct_size.setter
    def struct_size(self, value):
        self._struct_size = value

    @property
    def struct_format(self):
        """ Struct format where pack/unpack used. """
        return self._struct_format

    @struct_format.setter
    def struct_format(self, value):
        self._struct_format = value

    @property
    def queue(self):
        """ Cross threaded queue for inbound data. """
        return self._queue

    @property
    def local_uid(self):
        """ UID of the sub-subsystem. """
        return self._local_uid

    def unpack(self):
        """
        Read out queued up data according to the protocol in use (to list if MQTT and struct if TCP).
        NOTE: Probable bottleneck due to making data uniform (independent of protocol), consider
        improvements, or use an alternative reader, if this turns out to be an issue.
        """
        result = []
        if not self.queue.empty():
            if (self._endpoint.protocol == base.Protocol.MQTT) or (self._endpoint.protocol == base.Protocol.MQTTS):
                unpack_range = range(0, self.queue.qsize() - 1)
                for _ in unpack_range:
                    result.append(self.queue.get())
                    # self.queue.task_done()
            elif self._endpoint.protocol == base.Protocol.TCP and self.struct_format:
                result = struct.iter_unpack(
                    self.struct_format, self.queue.get())
                # self.queue.task_done()
        return result

    async def loop_async(self):
        """ Initialize a new connection according to the configured endpoint. """
        if (self._endpoint.protocol == base.Protocol.MQTT) or (self._endpoint.protocol == base.Protocol.MQTTS):
            await self.initialize_mqtt_subscriber(self._loop_iteration)
        elif self._endpoint.protocol == base.Protocol.TCP:
            await self.initialize_tcp_sink(self._loop_iteration)
        else:
            self._is_started = False
            print(f"{base.Style.ERROR}unimplemented protocol {self._endpoint.protocol}, input channel cannot be initialized.{base.Style.EOS}", flush=True)
            self.status = base.Status.FAILURE

    async def purge_loop_async(self):
        """ Keep queues cleared where not started. """
        loop_iteration_at_init = self.loop_iteration
        while self._is_shutting_down or (not self._is_started and (loop_iteration_at_init == self.loop_iteration)):
            try:
                while True:
                    self._queue.get_nowait()
            except:
                pass
            if self._is_shutting_down:
                break
            await asyncio.sleep(FORCED_QUEUE_CLEANUP_INTERVAL)

    # -----------------------------------------------------------------------------
    async def initialize_mqtt_subscriber(self, loop_iteration_at_init):
        """ Initialize data input through MQTT. """
        client = mqtt.Client(client_id=f"{self.local_uid}_incoming", clean_session=True,
                             userdata=self, protocol=mqtt.MQTTv311, transport='tcp')
        if self._endpoint.protocol == base.Protocol.MQTTS:
            # Enables TLS1.2 with externally provided keys/certificates
            client.tls_set(None, None, None, cert_reqs=ssl.CERT_NONE,
                           tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
            # disables peer verification
            client.tls_insecure_set(True)
        # -------------------------------------------------------------------------
        client.is_connected = False
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        # -------------------------------------------------------------------------
        print(f"{base.Style.INFO}MQTT subscriber connecting on {self._endpoint.ip_address}:{self._endpoint.port}{' with TLS support' if self._endpoint.protocol == base.Protocol.MQTTS else ''}...{base.Style.EOS}")
        client.connect_async(self._endpoint.ip_address,
                             self._endpoint.port, 60)
        # -------------------------------------------------------------------------
        # Initialize connection to the broker as configured
        client.loop_start()
        # Wait for connection setup to complete
        while not client.is_connected:
            await asyncio.sleep(1)
        # -------------------------------------------------------------------------
        while self._endpoint.is_active and self._is_started and (loop_iteration_at_init == self.loop_iteration):
            await asyncio.sleep(CANCELLATION_CHECK_INTERVAL)
        # -------------------------------------------------------------------------
        print(f"{base.Style.INFO}MQTT subscriber disconnecting...{base.Style.EOS}")
        client.disconnect()
        while client.is_connected:
            await asyncio.sleep(CANCELLATION_CHECK_INTERVAL)
        client.loop_stop()

    async def initialize_tcp_sink(self, loop_iteration_at_init):
        """ Initialize data input through raw TCP. """
        self._event_loop = asyncio.get_event_loop()
        server = await self._event_loop.create_server(
            lambda: CustomProtocol(self._endpoint, self._queue, self._activity_queue),
            self._endpoint.ip_address, self._endpoint.port, reuse_address=True)
        # -------------------------------------------------------------------------
        print(f"{base.Style.INFO}TCP data sink connection for {self._endpoint.ip_address}:{self._endpoint.port}...{base.Style.EOS}")
        # -------------------------------------------------------------------------

        async def termination_check(server):
            while self._is_started and (loop_iteration_at_init == self.loop_iteration):
                await asyncio.sleep(CANCELLATION_CHECK_INTERVAL)
            server.pause_reading()
            print(f"{base.Style.INFO}TCP data sink disconnecting...{base.Style.EOS}")
            server.close()
            server.wait_closed()
        # Initialize connection to the broker as configured
        async with server:
            termination_check_task = asyncio.create_task(
                termination_check(server))
            await server.serve_forever()
            await termination_check_task
