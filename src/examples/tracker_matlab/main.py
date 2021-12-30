#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Basic sub-system initialization and primary logic loop definition
"""

import asyncio
import mmap
import os
import struct
import threading
import time

import matlab.engine
import oddimorf
import yaml

from oddimorf import Style

# NOTE: Remember to have Matlab session open in LOCAL DIRECTORY with a share.
# share_engine_name = 'TRACKER_ENGINE'
share_engine_name = None
header_size_bytes = 4096
max_incoming_buffer_items = 90 * 128  # resolution cell count
max_outgoing_buffer_items = 16384
update_interval_sec = 0.25
interpreter = None
readers = []
writers = []


class Reader(threading.Thread):
    """ Thread used to read incoming data to the logic engine's input MMF. """

    def __init__(self, channel, key, sensor_origin):
        super().__init__()
        self.is_running = True
        self.channel = channel
        self.key = key
        self.sensor_origin = sensor_origin

    def run(self):
        """ Start the reader thread loop. """
        print(
            f"{Style.MISC}[INC] {self.channel.stream_key}: {self.channel.struct_format}{Style.EOS}")
        rabbit = 0
        max_size_bytes = self.channel.struct_size * max_incoming_buffer_items
        # ---------------------------------------------------------------------
        with open(os.path.join(os.path.dirname(__file__), f"_{self.key}.dat"), "wb") as file:
            file.truncate(header_size_bytes + max_size_bytes)
        # ---------------------------------------------------------------------
        with open(os.path.join(os.path.dirname(__file__), f"_{self.key}.dat"), 'r+b') as file:
            mm = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_WRITE)
            buffer = memoryview(mm)
            struct.pack_into('<l', buffer, 0, max_size_bytes)
            struct.pack_into('<l', buffer, 8, self.channel.struct_size)
            struct.pack_into('<Q', buffer, 24, round(time.time_ns() * 1E-6))
            struct.pack_into('<ff', buffer, 32,
                             self.sensor_origin[0], self.sensor_origin[1])
            struct.pack_into('<Q', buffer, 40, 4000)
            while self.is_running:
                time.sleep(0.1)
                if self.channel.queue.empty():
                    continue
                for packet in self.channel.unpack():
                    struct.pack_into('<l', buffer, 16, rabbit)
                    struct.pack_into(self.channel.struct_format, buffer, header_size_bytes + rabbit,
                                     int(packet[0]), float(packet[1]), float(packet[2]), float(packet[3]), float(packet[4]), float(packet[5]), int(packet[6]))
                    rabbit = (
                        rabbit + self.channel.struct_size) % max_size_bytes

    def stop(self):
        """ Terminate the reader thread loop. """
        self.is_running = False
        print(f"{Style.INFO}terminating Python to Matlab reader...{Style.EOS}")


class Interpreter(threading.Thread):
    """ Thread used to manage the primary logic engine thread. """

    def update_control_data(self):
        with open(os.path.join(os.path.dirname(__file__), f"_Control.dat"), 'r+b') as file:
            mm = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_WRITE)
            buffer = memoryview(mm)
            struct.pack_into('<lIQI', buffer, 0, 0, header_size_bytes, 0, 0)
            # -----------------------------------------------------------------
            # Custom fields
            struct.pack_into('<I', buffer, 16, self._required_detections)

    # Control data transfer functions
    def set_required_detections(self, value):
        if self._required_detections != value:
            self._required_detections = value
            self.update_control_data()

    def __init__(self, share_engine_name):
        super().__init__()
        self.is_running = True
        self.is_use_share_engine = share_engine_name is not None
        # ---------------------------------------------------------------------
        # Custom control data fields
        self._required_detections = 2
        # ---------------------------------------------------------------------
        if self.is_use_share_engine:
            shared_engine_names = matlab.engine.find_matlab()
            if share_engine_name in shared_engine_names:
                self.future = matlab.engine.connect_matlab(
                    share_engine_name, background=True)
                print(
                    f"{Style.INFO}connecting to shared Matlab engine at '{share_engine_name}'...{Style.EOS}")
            else:
                print(f"{Style.ERROR}Matlab share engine \"{share_engine_name}\" not be found, verify that session is running with the specified engine.{Style.EOS}")
        else:
            self.future = matlab.engine.start_matlab("-nojvm", background=True)
            print(f"{Style.INFO}starting up new Matlab engine...{Style.EOS}")
        # ---------------------------------------------------------------------
        self.eng = self.future.result()
        print(f"{Style.INFO}new Matlab engine started.{Style.EOS}")
        self.eng.cleanup(nargout=0)
        # ---------------------------------------------------------------------
        with open(os.path.join(os.path.dirname(__file__), f"_Control.dat"), "wb") as file:
            file.truncate(16384)
        # ---------------------------------------------------------------------
        self.update_control_data()

    def run(self):
        """ Start the interpreter's associated logic engine. """
        if self.is_running:
            self.eng.process(nargout=0)
            # -----------------------------------------------------------------
            if self.is_use_share_engine:
                print(
                    f"{Style.INFO}disconnecting from shared Matlab engine...{Style.EOS}")
            else:
                print(f"{Style.INFO}terminating Matlab engine...{Style.EOS}")
            self.eng.quit()
        else:
            print(f"{Style.INFO}startup of Matlab engine aborted.{Style.EOS}")

    def stop(self):
        """ Terminate the interpreter thread and update the controller MMF's termination flag. """
        self.is_running = False
        print(
            f"{Style.INFO}terminating interpreter thread holding the logic engine...{Style.EOS}")
        # ---------------------------------------------------------------------
        with open(os.path.join(os.path.dirname(__file__), f"_Control.dat"), 'r+b') as file:
            mm = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_WRITE)
            buffer = memoryview(mm)
            struct.pack_into('<l', buffer, 0, 1)


class Writer(threading.Thread):
    """ Thread used to write outgoing data from a specific logic engine output MMF. """

    def __init__(self, key, pipe):
        super().__init__()
        self.is_running = True
        self.key = key
        self.pipe = pipe
        self.rabbit = 0
        self.struct_format = self.pipe['struct_format']
        self.field_formats = self.pipe['struct_field_formats']
        self.queue = self.pipe['queue']
        self.struct_size = pipe['struct_size']
        self.field_sizes = pipe['struct_field_sizes']
        max_size_bytes = pipe['struct_size'] * max_outgoing_buffer_items
        # ---------------------------------------------------------------------
        with open(os.path.join(os.path.dirname(__file__), f"_{self.key}.dat"), "wb") as file:
            file.truncate(header_size_bytes + max_size_bytes)
        # ---------------------------------------------------------------------
        with open(os.path.join(os.path.dirname(__file__), f"_{self.key}.dat"), 'r+b') as file:
            mm = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_WRITE)
            buffer = memoryview(mm)
            struct.pack_into('<l', buffer, 0, max_size_bytes)
            struct.pack_into('<l', buffer, 8, pipe['struct_size'])
            struct.pack_into('<Q', buffer, 24, int(time.time_ns() * 1E-6))
        # ---------------------------------------------------------------------
        print(f"{Style.MISC}[OUT] {self.key}: {self.struct_format}{Style.EOS}")

    def unpack_blocks(self, buffer, from_index, to_index):
        block_start = header_size_bytes
        number_of_fields = len(self.field_formats)
        items = [[0]*number_of_fields for _ in range(to_index - from_index)]
        for i in range(number_of_fields):
            field_format = self.field_formats[i]
            field_size = self.field_sizes[i]
            for j in range(to_index - from_index):
                if "s" in field_format:
                    items[j][i] = struct.unpack_from(field_format, buffer, block_start + (
                        (j + from_index) * field_size))[0].partition(b'\00')[0].decode()
                else:
                    items[j][i] = struct.unpack_from(
                        field_format, buffer, block_start + ((j + from_index) * field_size))[0]
            block_start = block_start + \
                (max_outgoing_buffer_items * field_size)
        [self.queue.put(items[j]) for j in range(to_index - from_index)]

    def run(self):
        """ Start the writer thread loop. """
        read_head = 0
        write_head = 0
        # ---------------------------------------------------------------------
        with open(os.path.join(os.path.dirname(__file__), f'_{self.key}.dat'), 'rb') as file:
            mm = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
            buffer = memoryview(mm)
            while self.is_running:
                write_head = struct.unpack_from('<l', buffer, 16)[0]
                if write_head == read_head:
                    time.sleep(update_interval_sec)
                    continue
                while (read_head != write_head) and self.is_running:
                    if write_head < read_head:
                        self.unpack_blocks(
                            buffer, read_head, max_outgoing_buffer_items)
                        self.unpack_blocks(buffer, 0, write_head)
                    else:
                        self.unpack_blocks(buffer, read_head, write_head)
                    read_head = write_head

    def stop(self):
        """ Terminate the writer thread loop. """
        self.is_running = False
        print(
            f"{Style.INFO}terminating {self.key} Matlab to Python writer...{Style.EOS}")


async def loop_async(context, _):
    """ Primary execution logic of the sub-system. """
    while context.input_channel.struct_size <= 0:
        print(f"{Style.INFO}awaiting input channel details...{Style.EOS}")
        await asyncio.sleep(4)
    # -------------------------------------------------------------------------
    # Incoming/Read queue
    readers.append(Reader(context.input_channel,
                          'Plots', context.sensor_origin))
    # -------------------------------------------------------------------------
    # Outgoing/Write queues
    for key in context.output_channel.stream_keys:
        writers.append(Writer(key, context.output_channel.pipes[key]))
    # -------------------------------------------------------------------------
    # Control setup
    required_detections_slider = context.controls[0]
    required_detections_slider.set_map_range(2*8)
    required_detections_slider.observe(
        'received', lambda: interpreter.set_required_detections(required_detections_slider.value))
    interpreter.set_required_detections(required_detections_slider.value)
    # -------------------------------------------------------------------------
    for writer in writers:
        writer.start()
    interpreter.start()
    for reader in readers:
        reader.start()
    # -------------------------------------------------------------------------
    with open(os.path.join(os.path.dirname(__file__), f"_Control.dat"), 'r+b') as file:
        mm = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_WRITE)
        buffer = memoryview(mm)
        while not context.is_terminated:
            struct.pack_into('<Q', buffer, 8, round(time.time_ns() * 1E-6))
            await asyncio.sleep(update_interval_sec)


async def main():
    """ Entry function to the sub-system. """
    context = None
    try:
        with open(os.path.join(os.path.dirname(__file__), 'config.yml'), 'r') as config_file:
            config = yaml.load(config_file, Loader=yaml.FullLoader)
    except:
        raise ValueError("Missing or invalid configuration provided.")
    # -------------------------------------------------------------------------
    context = oddimorf.Context(config)
    controller = oddimorf.Controller(context)
    # -------------------------------------------------------------------------
    try:
        await controller.start_async()
        await loop_async(context, config)
    except Exception as x:
        print(f'{Style.ERROR}process loop interrupted with:  -> \"{x}\"{Style.EOS}')
    finally:
        print(f"{Style.WARNING}terminating...{Style.EOS}")
        await controller.stop_async()

interpreter = Interpreter(share_engine_name)
# -----------------------------------------------------------------------------
# Execute requisite logic
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"{Style.ERROR}process loop manually interrupted{Style.EOS}")
    except Exception as e:
        print(f"{Style.ERROR}{e}{Style.EOS}")
    finally:
        try:
            # Additional finalizer calls
            interpreter.stop()
            if readers:
                for reader in readers:
                    reader.stop()
            if writers:
                for writer in writers:
                    writer.stop()
        finally:
            print('___\n')
            exit()
