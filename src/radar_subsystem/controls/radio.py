#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Radio button collection control classes an logic.
"""

import json
import struct

from ..base import Control, Event


class RadioControl(Control):
    """ Selection of an indexed value from a list of values, presented as a radio control """

    def __init__(self, control_config):
        super().__init__(control_config)
        self._items = control_config['items']
        self._selected = control_config['selected']
        self._start_pos = 0
        self._end_pos = 0

    @property
    def data_length(self):
        """ Data length size of item """
        return 8

    @property
    def end_pos(self):
        """ [OPTIONAL] End index of item in memory map. """
        return self._end_pos

    @property
    def items(self):
        """ Array of items available for selection """
        return self._items

    @property
    def selected(self):
        """ Index of the currently selected value from the collection of available items """
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value

    def set_map_range(self, start_pos):
        """ Set the start and end indices to use in an associated memory map for interop """
        self._start_pos = start_pos
        self._end_pos = start_pos + self.data_length

    def write_to_mem_map(self, buffer):
        """ Get byte array format for message value from current instance """
        struct.pack_into('<q', buffer, self._start_pos, self.selected)

    def from_input(self, payload):
        """ Update instance from message payload """
        incoming_control = self.decode(payload)
        if incoming_control:
            self._selected = int(incoming_control['selected'])
        Event('received')

    def to_output(self):
        """ Get unmapped format for message payload from current instance """
        return json.dumps({
            'type': self._type,
            'label': self._label,
            'selected': self._selected,
            'items': self._items
        })
