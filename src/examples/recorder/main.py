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
max_structs_count = 2**17
recorders = []


class Counter(object):
    """ Cross-threaded sequence counter. """

    def __init__(self):
        self._lock = threading.Lock()
        self._count = 0

    @property
    def count(self):
        """ Counter value. """
        return self._count

    def increment(self):
        """ Increment counter count by 1 """
        self._lock.acquire()
        try:
            self._count = self._count + 1
        finally:
            self._lock.release()

    def reset(self):
        """ Reset counter count to 0 """
        self._lock.acquire()
        try:
            self._count = 0
        finally:
            self._lock.release()


class Recorder(threading.Thread):
    """ Thread used to read incoming data to the logic engine's input MMF. """

    def __init__(self, output_directory, channel, key, sensor_origin, counter):
        super().__init__()
        self.is_running = True
        self._is_halted = True
        self.output_directory = output_directory
        self.channel = channel
        self.key = key
        self.sensor_origin = sensor_origin
        self.counter = counter

    def run(self):
        """ Start the reader thread loop. """
        print(
            f"{Style.MISC}[INC] {self.channel.stream_key}: {self.channel.struct_format}{Style.EOS}")
        rabbit = 0
        max_size_bytes = (self.channel.struct_size + 8) * max_structs_count
        # ---------------------------------------------------------------------
        file_sequence = 0
        write_head = 0
        packets = []
        time.sleep(2)
        while self.is_running:
            while self._is_halted:
                time.sleep(0.1)
                if self.is_running:
                    continue
                else:
                    return
            structs_in_file = 0
            print(
                f"{Style.INFO} > recording {self.key} #{file_sequence} (max {max_structs_count} structs)...{Style.EOS}")
            # -----------------------------------------------------------------
            prev_output_directory = self.output_directory
            output_file = (self.output_directory +
                           '/' if self.output_directory and self.output_directory[-1] != '/' else self.output_directory) + f"_{self.key}_{file_sequence}.dat"
            # -----------------------------------------------------------------
            with open(os.path.join(os.path.dirname(__file__), output_file), "wb") as file:
                file.truncate(header_size_bytes + max_size_bytes)
            # -----------------------------------------------------------------
            with open(os.path.join(os.path.dirname(__file__), output_file), 'r+b') as file:
                mm = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_WRITE)
                buffer = memoryview(mm)
                rabbit = 0
                struct.pack_into('<l', buffer, 0, max_size_bytes)
                struct.pack_into('<l', buffer, 8, self.channel.struct_size + 8)
                struct.pack_into('<l', buffer, 16, write_head)
                struct.pack_into('<Q', buffer, 32,
                                 round(time.time_ns() * 1E-6))
                struct.pack_into('<ff', buffer, 40,
                                 self.sensor_origin[0], self.sensor_origin[1])
                while self.is_running & (structs_in_file < max_structs_count):
                    if self.output_directory != prev_output_directory:
                        file_sequence = 0
                        break
                    time.sleep(0.1)
                    if self.channel.queue.empty():
                        continue
                    for p in self.channel.unpack():
                        packets.append(p)
                    while self.is_running & (structs_in_file < max_structs_count) & (len(packets) > 0):
                        packet = packets.pop()
                        struct.pack_into('<l', buffer, 24, write_head)
                        struct.pack_into(
                            '<Q', buffer, header_size_bytes + rabbit, self.counter.count)
                        struct.pack_into(self.channel.struct_format, buffer, header_size_bytes + rabbit + 8, int(
                            packet[0]), float(packet[1]), float(packet[2]), float(packet[3]), float(packet[4]))
                        rabbit = (rabbit + self.channel.struct_size +
                                  8) % max_size_bytes
                        write_head = write_head + 1
                        structs_in_file = structs_in_file + 1
            file_sequence = file_sequence + 1

    def set_output_directory(self, output_directory):
        """ Set the output directory to use for placing recorded data files. """
        self.output_directory = output_directory
        print(f"{Style.INFO}output directory set to \"{self.output_directory}\" on the {self.key} Matlab to Python recorder...{Style.EOS}")

    def stop(self):
        """ Terminate the reader thread loop. """
        self.is_running = False
        print(f"{Style.INFO}terminating {self.key} recorder...{Style.EOS}")

    def halt(self):
        """ Halts the recording, may be initialized again with subsequent restart."""
        self._is_halted = True

    def restart(self):
        """ Restarts the recording from the 0th file sequence."""
        self._file_sequence = 0
        self._is_halted = False


async def loop_async(context, _):
    """ Primary execution logic of the sub-system. """
    # -------------------------------------------------------------------------
    counter = Counter()
    while context.input_channel.struct_size + 8 <= 0:
        print(context.input_channel.struct_size)
        print(f"{Style.INFO}awaiting input channel details...{Style.EOS}")
        await asyncio.sleep(4)
    # -------------------------------------------------------------------------
    output_directory = ''
    # -------------------------------------------------------------------------
    await asyncio.sleep(1)
    while len(context.controls) <= 0:
        print(f"{Style.INFO}awaiting output details...{Style.EOS}")
        await asyncio.sleep(4)
    recorders.append(Recorder(
        context.controls[0].value, context.input_channel, 'Raw', context.sensor_origin, counter))
    # -------------------------------------------------------------------------
    for recorder in recorders:
        recorder.start()
    # -------------------------------------------------------------------------
    await asyncio.sleep(2)
    counter.reset()
    is_started_prev = False
    while not context.is_terminated:
        if context.is_running & ~is_started_prev:
            counter.reset()
            for recorder in recorders:
                recorder.restart()
            is_started_prev = True
        elif ~context.is_running & is_started_prev:
            for recorder in recorders:
                recorder.halt()
            is_started_prev = False

        await asyncio.sleep(0.25)
        counter.increment()
        if output_directory != context.controls[0].value:
            output_directory = context.controls[0].value
            for recorder in recorders:
                recorder.set_output_directory(output_directory)


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
            if recorders:
                for recorder in recorders:
                    recorder.stop()
        finally:
            print('___\n')
            exit()
