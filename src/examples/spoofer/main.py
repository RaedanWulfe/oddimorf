#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Basic sub-system initialization and primary logic loop definition
"""

import asyncio
import os
import random
import time

import oddimorf
import yaml

from oddimorf import Style
from geopy.distance import distance


async def loop_async(context, _):
    """ Primary execution logic of the sub-system. """
    # -------------------------------------------------------------------------
    # Outgoing/Write queues
    cluttermap_queue = context.output_channel.pipes['ClutterMap']['queue']
    plots_queue = context.output_channel.pipes['Plots']['queue']
    strobes_queue = context.output_channel.pipes['Strobes']['queue']
    tracks_queue = context.output_channel.pipes['Tracks']['queue']
    # -------------------------------------------------------------------------
    # Control setup
    interval_slider = context.controls[0]
    cluttermap_mode = context.controls[1]
    cluttermap_slider = context.controls[2]
    plots_mode = context.controls[3]
    plots_slider = context.controls[4]
    strobes_slider = context.controls[5]
    tracks_mode = context.controls[6]
    tracks_slider = context.controls[7]
    # -------------------------------------------------------------------------
    _cluttermap_buffer = []
    _plots_buffer = []
    _strobes_buffer = []
    _tracks_buffer = []
    current_time_msec = 0
    block_send_time_msec = 0
    block_sequence = 0
    block_start_angle = 0
    sector_count = 0
    # -------------------------------------------------------------------------
    rng = 0
    az = 0
    intensity = 0
    speed = 0
    type = 0
    bearing = 0
    destination = None
    tracks_popup = "Extended Info:<br/>This is completely dynamic</br> and can place <p style='color:red;'><b>whatever</b></p>you want here.</p>"
    # -------------------------------------------------------------------------
    # Processing loop
    while not context.is_terminated:
        if not context.is_running:
            await asyncio.sleep(0.1)
            continue
        # ---------------------------------------------------------------------
        current_time_msec = int(round(time.time_ns() * 1E-6))
        if current_time_msec > block_send_time_msec:
            block_send_time_msec = current_time_msec
        await asyncio.sleep(max(block_send_time_msec - current_time_msec, 1) * 1E-03)
        # ---------------------------------------------------------------------
        if cluttermap_slider.value > 0:
            while len(_cluttermap_buffer) > 0:
                cluttermap_queue.put(_cluttermap_buffer.pop())
        else:
            _cluttermap_buffer.clear()
        if context.is_running and plots_slider.value > 0:
            while len(_plots_buffer) > 0:
                plots_queue.put(_plots_buffer.pop())
        else:
            _plots_buffer.clear()
        if context.is_running and strobes_slider.value > 0:
            while len(_strobes_buffer) > 0:
                strobes_queue.put(_strobes_buffer.pop())
        else:
            _strobes_buffer.clear()
        if context.is_running and tracks_slider.value > 0:
            if tracks_mode.selected == 0:
                while len(_tracks_buffer) > 0:
                    tracks_queue.put(_tracks_buffer.pop())
            elif sector_count % 16 == 0:
                while len(_tracks_buffer) > 0:
                    tracks_queue.put(_tracks_buffer.pop())
        else:
            _tracks_buffer.clear()
        # ---------------------------------------------------------------------
        block_send_time_msec = block_send_time_msec + int(interval_slider.value)
        block_start_angle = block_sequence * 22.5
        block_sequence = (block_sequence + 1) % 16
        # ---------------------------------------------------------------------
        if cluttermap_slider.value > 0:
            for i in range(0, int(cluttermap_slider.value)):
                # -------------------------------------------------------------
                if context.is_terminated:
                    continue
                # -------------------------------------------------------------
                if cluttermap_mode.selected == 0:
                    rng = random.randint(0, 15000)
                    az = block_start_angle + (random.randint(0, 44) * 0.5)
                    destination = distance(meters=rng).destination(
                        context.sensor_origin, az)
                    intensity = 10;#random.randint(1, 10)
                else:
                    destination = context.sensor_origin
                    intensity = 10
                # -------------------------------------------------------------
                _cluttermap_buffer.append([
                    destination.latitude,
                    destination.longitude,
                    intensity
                ])
        if plots_slider.value > 0:
            for i in range(0, int(plots_slider.value)):
                # -------------------------------------------------------------
                if context.is_terminated:
                    continue
                # -------------------------------------------------------------
                if plots_mode.selected == 0:
                    rng = random.randint(0, 15000)
                    az = block_start_angle + (random.randint(0, 44) * 0.5)
                    destination = distance(meters=rng).destination(
                        context.sensor_origin, az)
                    speed = random.randint(1, 300)
                    type = random.randint(0, 3)
                else:
                    rng = 15000
                    az = 100
                    destination = context.sensor_origin
                    speed = 300
                    type = 0
                # -------------------------------------------------------------
                _plots_buffer.append([
                    block_send_time_msec,
                    destination.latitude,
                    destination.longitude,
                    rng,
                    az,
                    speed,
                    type
                ])
        if strobes_slider.value > 0:
            for i in range(0, int(strobes_slider.value)):
                # -------------------------------------------------------------
                if context.is_terminated:
                    continue
                # -------------------------------------------------------------
                rng = random.randint(0, 15000)
                az = block_start_angle + (random.randint(0, 44) * 0.5)
                type = random.randint(0, 3)
                # -------------------------------------------------------------
                _strobes_buffer.append([
                    oddimorf.timestamp(),
                    (block_sequence * int(strobes_slider.value)) + i,
                    context.sensor_origin.latitude,
                    context.sensor_origin.longitude,
                    rng,
                    az,
                    type
                ])
        if tracks_slider.value > 0:
            for i in range(0, int(tracks_slider.value)):
                # -------------------------------------------------------------
                if context.is_terminated:
                    continue
                # -------------------------------------------------------------
                rng = random.randint(0, 15000)
                az = block_start_angle + (random.randint(0, 44) * 0.5)
                destination = distance(meters=rng).destination(
                    context.sensor_origin, az)
                bearing = az + 90
                speed = random.randint(1, 300)
                type = random.randint(0, 2)
                # -------------------------------------------------------------
                _tracks_buffer.append([
                    oddimorf.timestamp(),
                    f"{((block_sequence * int(tracks_slider.value)) + i):5}",
                    destination.latitude,
                    destination.longitude,
                    bearing,
                    speed,
                    type,
                    tracks_popup
                ])
        sector_count = sector_count + 1

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
        print('___\n')
        exit()
