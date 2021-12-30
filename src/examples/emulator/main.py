#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Basic sub-system initialization and primary logic loop definition
"""

import asyncio
import math
import os
import random
import time

import oddimorf
import yaml

from oddimorf import Style

max_range = 15000
max_tracks_per_block = 10
min_range = max_range / max_tracks_per_block
block_time_msec = 250
blocks_count = 16
cutoff_clutter_speed_ms = 50
max_clutter_speed_ms = 250
cutoff_clutter_intensity = 15
max_clutter_intensity = 20
block_azimuth_span = 22.5
azimuth_resolution = 0.5
range_increment = 10
azimuth_increment = 1.0
randomization_factor = block_azimuth_span / azimuth_resolution
tan_05 = math.tan(0.5 * math.pi / 180)


async def loop_async(context, _):
    """ Primary execution logic of the sub-system. """
    queue = context.output_channel.pipes['Raw']['queue']
    block_sequence = 0
    comp_start_time_msec = round(time.time_ns() * 1E-6)
    plot_radials = []
    for i in range(0, blocks_count):
        plot_radials.append([])
        for j in range(0, max_tracks_per_block):
            plot_radials[i].append(
                [(j + 1) * int(max_range / (max_tracks_per_block + 1)), (i + 0.5) * block_azimuth_span])
    while not context.is_terminated:
        if not context.is_running:
            await asyncio.sleep(0.1)
            continue
        start_angle = block_sequence * block_azimuth_span
        comp_start_time_msec = round(time.time_ns() * 1E-6)
        for _ in range(0, int(context.controls[0].value)):
            # -----------------------------------------------------------------
            if context.is_terminated:
                continue
            # -----------------------------------------------------------------
            rng = random.randint(0, max_range)
            az = start_angle + \
                (random.randint(0, randomization_factor) * azimuth_resolution)
            intensity = random.randint(0, cutoff_clutter_intensity)
            speed = random.randint(0, cutoff_clutter_speed_ms)
            # -----------------------------------------------------------------
            queue.put([
                comp_start_time_msec,
                rng,
                az,
                speed,
                intensity
            ])
        for j in range(0, int(context.controls[1].value)):
            # -----------------------------------------------------------------
            if context.is_terminated:
                continue
            # -----------------------------------------------------------------
            plot_radials[block_sequence][j][0] = plot_radials[block_sequence][j][0] + \
                range_increment if plot_radials[block_sequence][j][0] < max_range else min_range
            plot_radials[block_sequence][j][1] = plot_radials[block_sequence][j][1] + \
                azimuth_increment if plot_radials[block_sequence][j][1] < 360 else azimuth_increment
            intensity = random.randint(
                cutoff_clutter_intensity + 1, max_clutter_intensity)
            speed = plot_radials[block_sequence][j][0] * tan_05
            # -----------------------------------------------------------------
            queue.put([
                comp_start_time_msec,
                plot_radials[block_sequence][j][0],
                plot_radials[block_sequence][j][1],
                speed,
                intensity
            ])
        comp_delta_time_msec = round(
            time.time_ns() * 1E-6) - comp_start_time_msec
        block_sequence = (block_sequence + 1) % blocks_count
        if comp_delta_time_msec < block_time_msec:
            await asyncio.sleep((block_time_msec - comp_delta_time_msec) * 1E-3)


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
