#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Basic sub-system initialization and primary logic loop definition
"""

import asyncio
import os

import oddimorf
import yaml

from oddimorf import Style


async def loop_async(context, config):
    """ Primary execution logic of the sub-system. """
    # -------------------------------------------------------------------------
    # Incoming/Read queue
    readQueue = context.input_channel.queue
    # -------------------------------------------------------------------------
    # Outgoing/Write queues
    # TODO
    # -------------------------------------------------------------------------
    # Control setup
    # TODO
    # -------------------------------------------------------------------------
    # Processing loop
    while not context.is_terminated:
        if not context.is_running or not readQueue or readQueue.empty():
            await asyncio.sleep(0.1)
            continue
        # ---------------------------------------------------------------------
        # TODO
        while context.is_running and readQueue and not readQueue.empty():
            for todo in context.input_channel.unpack():
                # TODO
                None


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
