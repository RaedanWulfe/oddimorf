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

import oddimorf
import yaml

from oddimorf import Style

header_size_bytes = 4096
feeders = []


class Feeder(threading.Thread):
    """ Thread used to write outgoing data from a specific logic engine output MMF. """

    def __init__(self, context, key, pipe):
        super().__init__()
        self.context = context
        self.is_running = True
        self.key = key
        self.pipe = pipe
        self.rabbit = 0
        self.struct_size = self.pipe['struct_size']
        self.struct_format = self.pipe['struct_format']
        self.field_formats = self.pipe['struct_field_formats']
        self.queue = self.pipe['queue']
        self.sequence_number = 0
        self.last_sequence_number = 0
        self.delay = self.context.controls[0].value * 1E-3
        self.input_directory = context.controls[1].value
        # ---------------------------------------------------------------------
        print(f"{Style.MISC}[OUT] {self.key}: {self.struct_format}{Style.EOS}")

    def unpack_structs(self, buffer, from_index, to_index):
        last_block_processing_time_msec = 0
        block_start_time_msec = round(time.time_ns() * 1E-6)
        for i in range(from_index, to_index):
            if not self.context.is_running:
                break
            if self.sequence_number > self.last_sequence_number:
                last_block_processing_time_msec = round(
                    time.time_ns() * 1E-6) - block_start_time_msec
                time.sleep(max(self.delay * (self.sequence_number -
                                             self.last_sequence_number) - last_block_processing_time_msec, 1E-3))
                self.last_sequence_number = self.sequence_number
                block_start_time_msec = round(time.time_ns() * 1E-6)
            self.rabbit = header_size_bytes + (i * (8 + self.struct_size))
            self.sequence_number = struct.unpack_from(
                '<Q', buffer, self.rabbit)[0]
            item = struct.unpack_from(
                self.struct_format, buffer, self.rabbit + 8)
            self.queue.put(item)

    def run(self):
        """ Start the feeder thread loop. """
        # ---------------------------------------------------------------------
        delayIntervalSlider = self.context.controls[0]
        inputDirTextBox = self.context.controls[1]
        # ---------------------------------------------------------------------
        delayIntervalSlider.observe(
            'received', lambda: self.set_delay(delayIntervalSlider.value))
        inputDirTextBox.observe(
            'received', lambda: self.set_input_directory(inputDirTextBox.value))
        # ---------------------------------------------------------------------
        while self.is_running:
            if self.context.is_running:
                self.feed_all()
            else:
                time.sleep(0.25)

    def feed_all(self):
        """ Start the feeder sequence from the beginning. """
        print(
            f"{Style.INFO}re-running the {self.key} feeder sequence from the start...{Style.EOS}")
        _, _, files = next(os.walk(os.path.realpath(
            self.input_directory)), (None, None, []))
        files_range = [int(f[:-4].split(f"_{self.key}_", 1).pop())
                       for f in files if f.startswith(f"_{self.key}_")]
        files_range.sort()
        input_file = (self.input_directory +
                      '/' if self.input_directory and self.input_directory[-1] != '/' else self.input_directory) + f"_{self.key}_{files_range[0]}.dat"
        with open(os.path.join(os.path.dirname(__file__), input_file), 'rb') as file:
            buffer = memoryview(
                mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ))
            self.sequence_number = struct.unpack_from(
                '<Q', buffer, header_size_bytes)[0]
            self.last_sequence_number = self.sequence_number
        for file_sequence in files_range:
            if not self.context.is_running:
                break
            print(
                f'{Style.INFO} > feeding {self.key} #{file_sequence} into system...{Style.EOS}')
            input_file = (self.input_directory +
                          '/' if self.input_directory and self.input_directory[-1] != '/' else self.input_directory) + f"_{self.key}_{file_sequence}.dat"
            with open(os.path.join(os.path.dirname(__file__), input_file), 'rb') as file:
                buffer = memoryview(
                    mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ))
                max_size_bytes, struct_size, write_start, write_head = struct.unpack_from(
                    "<QQQQ", buffer, 0)
                self.max_buffer_items = max(
                    int(max_size_bytes / (struct_size + 8)), write_head - write_start)
                self.unpack_structs(buffer, 0, self.max_buffer_items)
        if self.context.is_running:
            print(f"{Style.INFO}feeder sequence on {self.key} completed.{Style.EOS}")
        time.sleep(1)

    def set_delay(self, delay):
        """ Set the delay interval between blocks being fed. """
        self.delay = delay * 1E-3
        # print(f"{Style.INFO}block send interval set to {self.delay}s on the {self.key} feeder...{Style.EOS}")

    def set_input_directory(self, input_directory):
        """ Set the delay interval between blocks being fed. """
        self.input_directory = input_directory
        # print(f"{Style.INFO}changed the default input directory on the {self.key} feeder...{Style.EOS}")

    def stop(self):
        """ Terminate the writer thread loop. """
        self.is_running = False
        print(f"{Style.INFO}terminating {self.key} feeder...{Style.EOS}")


async def loop_async(context, _):
    """ Primary execution logic of the sub-system. """
    await asyncio.sleep(1)
    while len(context.controls) < 2:
        print(f"{Style.INFO}awaiting output details...{Style.EOS}")
        await asyncio.sleep(4)
    for key in context.output_channel.stream_keys:
        feeders.append(Feeder(context, key, context.output_channel.pipes[key]))
    # -------------------------------------------------------------------------
    await asyncio.sleep(1)
    # -------------------------------------------------------------------------
    for feeder in feeders:
        feeder.start()
    # -------------------------------------------------------------------------
    while not context.is_terminated:
        await asyncio.sleep(0.1)


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
            if feeders:
                for feeder in feeders:
                    feeder.stop()
        finally:
            print('___\n')
            exit()
