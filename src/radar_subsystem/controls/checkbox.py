#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Checkbox collection control classes an logic.
"""

import json
import struct

from ..base import Control, Event


class ToggleItem:
    """ Individual toggle item for use with check boxes """

    def __init__(self, item_config):
        self._label = item_config['label']
        self._is_checked = item_config['isChecked']

    @property
    def label(self):
        """ Item label """
        return self._label

    @property
    def is_checked(self):
        """ Current toggle state """
        return self._is_checked

    @is_checked.setter
    def is_checked(self, value):
        self._is_checked = value

    def from_input(self, incoming_item):
        """ Update instance from message payload """
        self._is_checked = incoming_item['isChecked']

    def to_output(self):
        """ Get unmapped format for message payload from current instance """
        return {'label': self._label, 'isChecked': self._is_checked}


class CheckBoxControl(Control):
    """ List of on/off toggles, presented as a check box control """

    def __init__(self, control_config):
        super().__init__(control_config)
        self._items = []
        for item_config in control_config['items']:
            self._items.append(ToggleItem(item_config))
        self._start_pos = 0
        self._end_pos = 0

    @property
    def data_length(self):
        """ Data length size of item """
        return len(self._items) * 1

    @property
    def end_pos(self):
        """ [OPTIONAL] End index of item in memory map. """
        return self._end_pos

    @property
    def items(self):
        """ Toggleable items and their current states """
        return self._items

    @items.setter
    def items(self, value):
        self._items = value

    def set_map_range(self, start_pos):
        """ Set the start and end indices to use in an associated memory map for interop """
        self._start_pos = start_pos
        self._end_pos = start_pos + self.data_length

    def write_to_mem_map(self, buffer):
        """ Get byte array format for message value from current instance """
        for i in range(0, self.data_length):
            pos = self._start_pos + i
            struct.pack_into('<?', buffer, pos, self._items[i].is_checked)

    def from_input(self, payload):
        """ Update instance from message payload """
        incoming_control = self.decode(payload)
        if incoming_control:
            for item in incoming_control['items']:
                next(l for l in self._items if l.label ==
                     item['label']).is_checked = item['isChecked']
        Event('received')

    def to_output(self):
        """ Get unmapped format for message payload from current instance """
        json_obj = {
            'type': self._type,
            'label': self._label,
            'items': []
        }

        for item in self._items:
            json_obj['items'].append(item.to_output())

        return json.dumps(json_obj)
