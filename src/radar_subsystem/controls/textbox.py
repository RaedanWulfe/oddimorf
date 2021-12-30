#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Textbox control classes an logic.
"""

import json
import struct

from ..base import Control, Event


class TextBoxControl(Control):
    """ Definition of a single value, presented as a simple textbox control """

    def __init__(self, control_config):
        super().__init__(control_config)
        self._value = control_config['value']
        self._start_pos = 0
        self._end_pos = 0

    @property
    def data_length(self):
        """ Data length size of item """
        return 254

    @property
    def end_pos(self):
        """ [OPTIONAL] End index of item in memory map """
        return self._end_pos

    @property
    def value(self):
        """ Current value associated with this control """
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    def set_map_range(self, start_pos):
        """ Set the start and end indices to use in an associated memory map for interop """
        self._start_pos = start_pos
        self._end_pos = start_pos + self.data_length

    def write_to_mem_map(self, buffer):
        """ Get byte array format for message value from current instance """
        struct.pack_into(f'<{self.data_length}s', buffer,
                         self._start_pos, bytes(self.value, 'utf-8'))

    def from_input(self, payload):
        """ Update instance from message payload """
        incoming_control = self.decode(payload)
        if incoming_control:
            self._value = incoming_control['value']
        Event('received')

    def to_output(self):
        """ Get unmapped format for message payload from current instance """
        return json.dumps({
            'type': self._type,
            'label': self._label,
            'value': self._value
        })
