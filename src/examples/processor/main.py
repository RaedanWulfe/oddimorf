#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Basic sub-system initialization and primary logic loop definition
"""

import asyncio
import os

import oddimorf
import yaml

from geopy.distance import distance
from oddimorf import Style


async def loop_async(context, _):
    """ Primary execution logic of the sub-system. """
    # -------------------------------------------------------------------------
    # Incoming/Read queue
    readQueue = context.input_channel.queue
    # -------------------------------------------------------------------------
    # Outgoing/Write queues
    clutterWriteQueue = context.output_channel.pipes['ClutterMap']['queue']
    plotsWriteQueue = context.output_channel.pipes['Plots']['queue']
    # -------------------------------------------------------------------------
    destination = [0, 0]
    intensity = 0
    intensity_value = 0
    range_value = 0
    azimuth_value = 0
    # -------------------------------------------------------------------------
    while not context.is_terminated:
        if not context.is_running or not readQueue or readQueue.empty():
            await asyncio.sleep(0.1)
            continue
        while context.is_running and clutterWriteQueue and readQueue and not readQueue.empty():
            for time_ms, range, azimuth, speed, intensity in context.input_channel.unpack():
                range_value = float(range)
                azimuth_value = float(azimuth)
                destination = distance(meters=range_value).destination(
                    context.sensor_origin, azimuth_value)
                intensity_value = float(intensity)
                clutterWriteQueue.put(
                    [destination.latitude, destination.longitude, intensity_value])
                if intensity_value >= context.controls[0].value:
                    plotsWriteQueue.put([int(time_ms), destination.latitude, destination.longitude, range_value, azimuth_value, float(
                        speed), 1 if (intensity_value >= 18) else 2 if (intensity_value >= 16) else 3])


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
