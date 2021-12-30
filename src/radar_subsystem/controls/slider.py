#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Slider control classes an logic.
"""

import json
import struct

from ..base import Control, Event


class SliderControl(Control):
    """ Value selection from a range of values, presented as a slider control """

    def __init__(self, control_config):
        super().__init__(control_config)
        self._min = control_config['min']
        self._max = control_config['max']
        self._value = control_config['value']
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
    def value(self):
        """ Current value associated with this control """
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        Event('received')

    def set_map_range(self, start_pos):
        """ Set the start and end indices to use in an associated memory map for interop """
        self._start_pos = start_pos
        self._end_pos = start_pos + self.data_length

    def write_to_mem_map(self, buffer):
        """ Get byte array format for message value from current instance """
        struct.pack_into('<q', buffer, self._start_pos, int(self.value))
        # memory_map[self._start_pos:self._end_pos] = (f'{self.value}'.zfill(self.data_length)).encode()

    def from_input(self, payload):
        """ Update instance from message payload """
        incoming_control = self.decode(payload)
        if incoming_control:
            self._value = int(incoming_control['value'])
        Event('received')

    def to_output(self):
        """ Get unmapped format for message payload from current instance """
        return json.dumps({
            'type': self._type,
            'label': self._label,
            'min': self._min,
            'max': self._max,
            'value': self._value
        })
