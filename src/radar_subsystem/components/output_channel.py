#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Output channel component type classes and functionality
"""

import asyncio
import concurrent.futures
import csv
import datetime
import io
import queue
import ssl
import struct
import paho.mqtt.client as mqtt

from .. import base

MQTT_SEND_INTERVAL = 0.25
CANCELLATION_CHECK_INTERVAL = 1
CONNECTION_RETRY_INTERVAL = 2
RECHECK_DATA_IN_QUEUE_INTERVAL = 0.05
MAX_SEND_BLOCK_BYTE_SIZE = 16384
FORCED_QUEUE_CLEANUP_INTERVAL = 0.5


def on_connect(client, channel, flags, result):
    """ The callback for CONNACK response from MQTT input server, where applicable. """
    print(f"{base.Style.OK}MQTT publisher connected{base.Style.EOS}")
    channel.endpoint.is_active = True
    client.is_connected = True
    channel.status = base.Status.OPERATIONAL


def on_disconnect(client, channel, result):
    """ The callback for DISCONNECT response from the server, where applicable. """
    if not result:
        print(f"{base.Style.WARNING}MQTT publisher disconnected{base.Style.EOS}")
    else:
        channel.status = base.Status.FAILURE
        channel._is_started = False
        print(f"{base.Style.ERROR}MQTT publisher terminated unexpectedly ({result}){base.Style.EOS}")
        raise Exception
    channel.endpoint.is_active = False
    client.is_connected = False


class OutputChannel(base.Component):
    """ Class defining the output channel component, not used with the Control and Recorder sub-system types. """

    def __init__(self, local_uid, config):
        super().__init__()
        self._local_uid = local_uid
        self._stream_keys = []
        self._blocks = {}
        self._pipes = {}

        if config is None:
            return

        for data_item in config:
            key = data_item['key']
            types = data_item['dataTypes']
            self._stream_keys.append(key)
            field_types = types.split(',')
            self._pipes[key] = {
                'struct_format': base.dataTypesToFormat(types) if types else None,
                'struct_field_formats': [base.dataTypesToFormat(field_types[i]) for i in range(len(field_types))] if types else None,
                'struct_size': base.dataTypesToSize(types) if types else 0,
                'struct_field_sizes': [base.dataTypesToSize(field_types[i]) for i in range(len(field_types))] if types else 0,
                'queue': queue.SimpleQueue()
            }
        self._endpoint = None
        self._writer = None

    @property
    def endpoint(self):
        """ Incoming connection details. """
        return self._endpoint

    @endpoint.setter
    def endpoint(self, value):
        self._endpoint = value

    @property
    def pipes(self):
        """ Dictionary of cross threaded queues for outbound data. """
        return self._pipes

    @property
    def stream_keys(self):
        """ Output data topic streams produced by the sub-system. """
        return self._stream_keys

    @property
    def local_uid(self):
        """ UID of the sub-subsystem. """
        return self._local_uid

    async def loop_async(self):
        """ Initialize a new connection according to the configured endpoint. """
        if (self._endpoint.protocol == base.Protocol.MQTT) or (self._endpoint.protocol == base.Protocol.MQTTS):
            await self.initialize_mqtt_publisher(self._loop_iteration)
        elif self._endpoint.protocol == base.Protocol.TCP:
            await self.initialize_tcp_sender(self._loop_iteration)
        else:
            self._is_started = False
            print(f"{base.Style.ERROR}unimplemented protocol {self._endpoint.protocol}, output channel cannot be initialized.{base.Style.EOS}", flush=True)
            self.status = base.Status.FAILURE

    async def purge_loop_async(self):
        """ Keep queues cleared where not started. """
        queues = []
        loop_iteration_at_init = self.loop_iteration
        while not self._is_started and (loop_iteration_at_init == self.loop_iteration):
            for key, pipe in self._pipes.items():
                if not pipe or pipe['queue'].empty():
                    continue
                queues.append(pipe['queue'])
            for queue in queues:
                try:
                    while True:
                        queue.get_nowait()
                except:
                    pass
            if self._is_shutting_down:
                break
            await asyncio.sleep(FORCED_QUEUE_CLEANUP_INTERVAL)

    # -----------------------------------------------------------------------------
    async def initialize_mqtt_publisher(self, loop_iteration_at_init):
        """ Initialize data output through MQTT. """
        client = mqtt.Client(client_id=f"{self.local_uid}_outgoing", clean_session=True,
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
        client.on_disconnect = on_disconnect
        for topic in self._endpoint.topics:
            indices = [index for index,
                       char in enumerate(topic) if char == '/']
            key = topic[indices[-2]+1:indices[-1]]
            stringIo = io.StringIO()
            self._blocks[key] = {
                'topic': topic,
                'write_buffer': stringIo,
                'writer': csv.writer(stringIo, quoting=csv.QUOTE_NONNUMERIC),
                'payloads': queue.SimpleQueue()
            }
        # -------------------------------------------------------------------------
        print(f"{base.Style.INFO}MQTT publisher connecting on {self._endpoint.ip_address}:{self._endpoint.port}{' with TLS support' if self._endpoint.protocol == base.Protocol.MQTTS else ''}...{base.Style.EOS}")
        client.connect_async(self._endpoint.ip_address,
                             self._endpoint.port, 60)
        # -------------------------------------------------------------------------
        # Initialize connection to the broker as configured
        client.loop_start()
        # Wait for connection setup to complete
        while not client.is_connected:
            await asyncio.sleep(1)
        default_time_delta = datetime.timedelta(0, MQTT_SEND_INTERVAL)
        next_send_at = None
        futures = []
        # -------------------------------------------------------------------------
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            while self._is_started and (loop_iteration_at_init == self.loop_iteration):
                next_send_at = datetime.datetime.utcnow() + default_time_delta
                for key, pipe in self._pipes.items():
                    if self._is_started:
                        await self.mqtt_sender(client, self._blocks[key])
                for key, pipe in self._pipes.items():
                    if self._is_started and pipe and not pipe['queue'].empty():
                        # await self.mqtt_writer(self._blocks[key], pipe)
                        futures.append(executor.submit(
                            asyncio.run, self.mqtt_writer(self._blocks[key], pipe)))
                for future in futures:
                    if future.done():
                        futures.remove(future)
                await asyncio.sleep(max(1E-3, (next_send_at - datetime.datetime.utcnow()).total_seconds()))
            executor.shutdown()
            for future in concurrent.futures.as_completed(futures):
                futures.remove(future)
        # -------------------------------------------------------------------------
        print(f"{base.Style.INFO}MQTT publisher disconnecting...{base.Style.EOS}")
        for topic in self._endpoint.topics:
            indices = [index for index,
                       char in enumerate(topic) if char == '/']
            key = topic[indices[-2]+1:indices[-1]]
            self._blocks[key]['write_buffer'].close()
        client.disconnect()
        while client.is_connected:
            await asyncio.sleep(CANCELLATION_CHECK_INTERVAL)
        client.loop_stop()

    async def initialize_tcp_sender(self, loop_iteration_at_init):
        """ Initialize data output through raw TCP. """
        # -------------------------------------------------------------------------
        await asyncio.sleep(3)
        topic = self._endpoint.topics[0]
        indices = [index for index, char in enumerate(topic) if char == '/']
        key = topic[indices[-2]+1:indices[-1]]
        pipe = self._pipes[key]
        # -------------------------------------------------------------------------
        print(f"{base.Style.INFO}TCP sender connecting to {self._endpoint.ip_address}:{self._endpoint.port}...{base.Style.EOS}")
        self._endpoint.is_active = True
        # -------------------------------------------------------------------------
        while self._is_started and (loop_iteration_at_init == self.loop_iteration):
            # await self.tcp_writer(pipe, loop_iteration_at_init)
            await asyncio.gather(self.tcp_writer(pipe, loop_iteration_at_init))
            if self._is_started:
                await asyncio.sleep(CONNECTION_RETRY_INTERVAL)
        # -------------------------------------------------------------------------
        print(f"{base.Style.WARNING}TCP sender disconnected{base.Style.EOS}")

    # -----------------------------------------------------------------------------
    async def mqtt_writer(self, block, pipe):
        """ Queue interpreter to packing of data for polled publishing. """
        first_entry = pipe['queue'].get()
        # pipe['queue'].task_done()
        entry_size = int(1.2 * sum(map(len, (str(element) for element in first_entry))))
        number_of_entries = pipe['queue'].qsize()
        total_size = number_of_entries * entry_size
        number_of_blocks = max(total_size // MAX_SEND_BLOCK_BYTE_SIZE, 1)
        block_length = number_of_entries // number_of_blocks
        self.activity_queue.put(number_of_entries)
        # -------------------------------------------------------------------------
        ranges = []
        from_entry_index = 0
        if number_of_blocks:
            for i in range(0, number_of_blocks):
                if not self._is_started:
                    return
                to_entry_index = from_entry_index + block_length
                ranges.append(range(from_entry_index, to_entry_index))
                from_entry_index = to_entry_index + 1
        ranges.append(range(from_entry_index, number_of_entries - 1))
        if not block['writer']:
            print(f"{base.Style.WARNING}Missing CSV writer", flush=True)
            self.endpoint.is_active = False
            self.is_running = False
            self.status = base.Status.FAILURE
            await self.start_async()
            return
        # -------------------------------------------------------------------------
        try:
            block['writer'].writerow(first_entry)
            for i in range(0, len(ranges)):
                for j in ranges[i]:
                    if self._is_started:
                        block['writer'].writerow(pipe['queue'].get())
                block['payloads'].put(block['write_buffer'].getvalue())
                block['write_buffer'].truncate(0)
                block['write_buffer'].seek(0)
        except Exception as x:
            print(f"{base.Style.WARNING}CSV writing terminated with:\n  -> \"{x}\"{base.Style.EOS}", flush=True)
            block['writer'] = None
            pass

    async def mqtt_sender(self, client, block):
        """ Dedicated publisher of previously packed message payloads to an associated topic. """
        payloads_count = block['payloads'].qsize()
        for i in range(0, payloads_count - 1):
            payload = block['payloads'].get()
            if payload and self._is_started:
                send_data = client.publish(block['topic'], payload)
                send_data.wait_for_publish()

    async def tcp_writer(self, pipe, loop_iteration_at_init):
        """ Queue interpreter to direct output stream. """
        queue = pipe['queue']
        if not queue:
            return
        writer = None
        wire_format = pipe['struct_format']
        # -------------------------------------------------------------------------
        try:
            _, writer = await asyncio.open_connection(self._endpoint.ip_address, self._endpoint.port)
            self._endpoint.is_active = True
            print(f"{base.Style.OK}TCP sender reconnected{base.Style.EOS}")
            while self._endpoint.is_active and self._is_started and (loop_iteration_at_init == self.loop_iteration):
                while not queue.empty() and self._is_started:
                    self.activity_queue.put(1)
                    writer.write(struct.pack(wire_format, *queue.get()))
                    await writer.drain()
                await asyncio.sleep(RECHECK_DATA_IN_QUEUE_INTERVAL)
        except Exception:
            if not self._is_started:
                print(f"{base.Style.INFO}TCP sender disconnecting...{base.Style.EOS}")
            else:
                print(f"{base.Style.INFO}TCP sender reconnecting...{base.Style.EOS}")
        finally:
            self._endpoint.is_active = False
            if writer is asyncio.StreamWriter:
                writer.close()
