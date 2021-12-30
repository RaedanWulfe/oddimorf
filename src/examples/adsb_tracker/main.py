#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Basic sub-system initialization and primary logic loop definition
"""

import asyncio
import os
import requests

import oddimorf
import json
import yaml

from oddimorf import Style


async def loop_async(context, config):
    """ Primary execution logic of the sub-system. """
    # -------------------------------------------------------------------------
    # Outgoing/Write queues
    tracksQueue = context.output_channel.pipes['Tracks']['queue']
    # -------------------------------------------------------------------------
    # Control setup
    latMinTextBox = context.controls[0]
    latMaxTextBox = context.controls[1]
    lngMinTextBox = context.controls[2]
    lngMaxTextBox = context.controls[3]
    # -------------------------------------------------------------------------
    # Custom config parameters
    url = config['adbsUrl']
    # -------------------------------------------------------------------------
    # Processing loop
    while not context.is_terminated:
        if not context.is_running:
            await asyncio.sleep(0.1)
            continue
        response = None
        try:
            response = requests.get(url.format(
                latMinTextBox.value,
                latMaxTextBox.value,
                lngMinTextBox.value,
                lngMaxTextBox.value))
        except Exception as x:
            print(f'{Style.ERROR}{x}{Style.EOS}')
        if (response is not None and response.ok):
            record = json.loads(response.content)
            track_states = record['states']
            if not track_states:
                continue
            for track_state in record['states']:
                # -------------------------------------------------------------
                if context.is_terminated:
                    continue
                # -------------------------------------------------------------
                icao24, callsign, origin_country, _, _, longitude, latitude, baro_altitude, on_ground, velocity, true_track, vertical_rate, _, _, squawk, _, _ = track_state
                velocity = velocity if velocity else 0
                vertical_rate = vertical_rate if vertical_rate else 0
                baro_altitude = baro_altitude if baro_altitude else 0
                climb_symbol = "&#8230;" if on_ground else "&#x25B2;" if vertical_rate > 0 else "&#x25BC;" if vertical_rate < 0 else "&#x25C7;"
                climb_colour = "goldenrod" if on_ground else "lime" if vertical_rate > 0 else "tomato" if vertical_rate < 0 else "grey"
                # -------------------------------------------------------------
                tracksQueue.put([
                    oddimorf.timestamp(),
                    icao24,
                    float(latitude),
                    float(longitude),
                    float(true_track),
                    float(velocity),
                    0,
                    f"<b>{callsign}</b> ({squawk})<br/>" +
                    f"<em>{origin_country}</em><hr/>" +
                    f"ALT: {int(baro_altitude)} m<br/>" +
                    f"C/R: <p style='display:inline;color:{climb_colour};'><b>{climb_symbol}</b></p>{abs(float(vertical_rate))} m/s<br/>" +
                    "</p>"
                ])
        await asyncio.sleep(10)


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
