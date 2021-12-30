#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Basic sub-system initialization and primary logic loop definition
"""

import asyncio
import datetime
import mmap
import os

import yaml
import oddimorf

from oddimorf import Style

control_file_name = '_Control'


async def loop_async(context, _):
    """ Primary execution logic of the sub-system. """
    print_status_to_console = context.controls[0]
    poll_write = context.controls[1]
    textbox0 = context.controls[2]
    togglegroup0 = context.controls[3]
    radiogroup0 = context.controls[4]
    slider0 = context.controls[5]
    # -------------------------------------------------------------------------
    with open(os.path.join(os.path.dirname(__file__), control_file_name + '.dat'), "wb") as f:
        f.truncate(16384)
    # -------------------------------------------------------------------------
    with open(os.path.join(os.path.dirname(__file__), control_file_name + '.dat'), "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE)
        buffer = memoryview(mm)
        # ---------------------------------------------------------------------
        textbox0.set_map_range(0)
        togglegroup0.set_map_range(textbox0.end_pos)
        radiogroup0.set_map_range(togglegroup0.end_pos)
        slider0.set_map_range(radiogroup0.end_pos)
        # ---------------------------------------------------------------------
        textbox0.observe('received', lambda: textbox0.write_to_mem_map(
            buffer) if poll_write.selected == 0 else None)
        togglegroup0.observe('received', lambda: togglegroup0.write_to_mem_map(
            buffer) if poll_write.selected == 0 else None)
        radiogroup0.observe('received', lambda: radiogroup0.write_to_mem_map(
            buffer) if poll_write.selected == 0 else None)
        slider0.observe('received', lambda: slider0.write_to_mem_map(
            buffer) if poll_write.selected == 0 else None)
        # ---------------------------------------------------------------------
        while not context.is_terminated:
            if context.is_running and poll_write.selected == 1:
                textbox0.write_to_mem_map(buffer)
                togglegroup0.write_to_mem_map(buffer)
                radiogroup0.write_to_mem_map(buffer)
                slider0.write_to_mem_map(buffer)
            # -----------------------------------------------------------------
            if context.is_running and print_status_to_console.selected == 0:
                print(f"""---
{datetime.datetime.utcnow()}
TextBox value:  {textbox0.value}
CheckBox items: {togglegroup0.items[0].label}:{togglegroup0.items[0].is_checked}
                {togglegroup0.items[1].label}:{togglegroup0.items[1].is_checked}
Radio selected: {radiogroup0.items[radiogroup0.selected]}
Slider value:   {slider0.value}""")
            # -----------------------------------------------------------------
            await asyncio.sleep(1)


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
