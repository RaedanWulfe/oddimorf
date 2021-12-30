#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Base sub-system definition
"""

import asyncio
import json
import ssl
import threading

import paho.mqtt.client as mqtt

from geopy import Point

from . import controls
from . import components

from .base import Component, Control, DataItem, Endpoint, Protocol, Status, Style, dataTypesToFormat, dataTypesToSize


class Context:
    """ Current active self._context of sub-system module. """
    _activity_rates = [0, 0, 0, 0, 0, 0]

    def __init__(self, config):
        self.module_uid = str.replace(config['uid'], '-', '')
        self.module_name = config['name']
        self._chain_uid = ""
        self._input_channel = components.InputChannel(self.module_uid)
        self._output_channel = components.OutputChannel(
            self.module_uid, config['dataSchema'] if 'dataSchema' in config else None)
        self._status = Status.UNKNOWN
        self._sensor_origin = Point(0, 0)
        self._is_chain_running = False
        self._is_running = False
        self._is_terminated = False
        self.broker = Endpoint(Protocol.MQTTS if config['broker']['useTls']
                               else Protocol.MQTT, config['broker']['ip'], config['broker']['port'])
        self.data_items = []
        if 'dataSchema' in config:
            for data_config in config['dataSchema']:
                self.data_items.append(DataItem(data_config))
        self.controls = []
        self.is_subsystem_chained = False
        for control_config in config['controlSchema']:
            if control_config['type'] == 'TextBox':
                self.controls.append(controls.TextBoxControl(control_config))
            elif control_config['type'] == 'Slider':
                self.controls.append(controls.SliderControl(control_config))
            elif control_config['type'] == 'Radio':
                self.controls.append(controls.RadioControl(control_config))
            elif control_config['type'] == 'CheckBox':
                self.controls.append(controls.CheckBoxControl(control_config))

    @property
    def is_terminated(self):
        """ Indicated finalization has been activated. """
        return self._is_terminated

    @property
    def chain_uid(self):
        """ Current selected (active) chain on the broker. """
        return self._chain_uid

    @chain_uid.setter
    def chain_uid(self, value):
        self._chain_uid = value

    @property
    def sensor_origin(self):
        """ Origin point of the associated sensor. """
        return self._sensor_origin

    @sensor_origin.setter
    def sensor_origin(self, value):
        self._sensor_origin = value

    @property
    def input_channel(self):
        """ Input channel handle. """
        return self._input_channel

    @property
    def output_channel(self):
        """ Output channel handle. """
        return self._output_channel

    @property
    def status(self):
        """ Allows for setting the user-defined component's status. """
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    @property
    def is_subsystem_chained(self):
        """ Indicates whether the sub-systems is registered to the active chain. """
        return self._is_subsystem_chained

    @is_subsystem_chained.setter
    def is_subsystem_chained(self, value):
        self._is_subsystem_chained = value

    @property
    def is_chain_running(self):
        """ Is chain operations set to execute. """
        return self._is_chain_running

    @is_chain_running.setter
    def is_chain_running(self, value):
        self._is_chain_running = value

    @property
    def is_running(self):
        """ Is chain operations set to execute and configured under the currently active chain. """
        return self._is_running

    @is_running.setter
    def is_running(self, value):
        self._is_running = value

    async def determine_throughput_rate(self):
        """ Returns a determined rate indicators for throughput from logged activity rates. """
        input_activity = 0
        input_activity_range = range(
            0, self.input_channel.activity_queue.qsize() - 1)
        for i in input_activity_range:
            input_activity += self.input_channel.activity_queue.get()
        output_activity = 0
        output_activity_range = range(
            0, self.output_channel.activity_queue.qsize() - 1)
        for i in output_activity_range:
            output_activity += self.output_channel.activity_queue.get()
        self._activity_rates.append(input_activity + output_activity)
        max_value = max(max(self._activity_rates), 1)
        self._activity_rates.pop(0)
        return ''.join([str((5 * x) // max_value) for x in self._activity_rates])

    async def determine_error_count(self):
        """ Returns a determined error count as a sum of error counts in sub-system components. """
        # errors = self._input_channel.error_count + self._process.error_count + self._output_channel.error_count
        return "000000"

    async def rates_to_output(self):
        """ Returns determined throughput indicators from logged activity rates on sub-system components. """
        return json.dumps({
            'total': await self.determine_throughput_rate(),
            'errors': await self.determine_error_count()
        })

    async def determine_status(self):
        """ Returns a determined status of the sub-system from the status of its components. """
        return Status.to_string(Status(max(
            self._status.value, self._input_channel.status.value, self._output_channel.status.value)))

    def terminate(self):
        """ Terminates the sub-system. """
        self.broker.is_active = False
        self._is_terminated = True


def on_connect(client, userdata, flags, result):
    """ The callback for CONNACK response from the server. """
    print(f"{Style.OK}MQTT controller connected{Style.EOS}")
    client.subscribe("SelectedChain")
    userdata.broker.is_active = True
    client.is_connected = True


def on_disconnect(client, userdata, result):
    """ The callback for DISCONNECT response from the server. """
    if not result:
        print(f"{Style.ERROR}MQTT controller unexpectedly terminated.{Style.EOS}")
    else:
        print(f"{Style.WARNING}MQTT controller disconnected.{Style.EOS}")
    userdata.broker.is_active = False
    client.user_data_set("")
    client.is_connected = False


def on_message(client, userdata, msg):
    """ The callback for PUBLISH message from the server. """
    # Restrict subscription to the active (selected) chain
    if msg.topic == "SelectedChain":
        if not msg.payload:
            return
        payload = json.loads(str(msg.payload.decode('utf-8')))
        userdata.chain_uid = payload['id']
        userdata.is_chain_running = payload['isRunning']
        client.subscribe(f"Chains/{userdata.chain_uid}/Setup")
        client.subscribe(f"Chains/{userdata.chain_uid}/Setup/SubSystems")
    elif msg.topic == f"Chains/{userdata.chain_uid}/Setup":
        # Basic information on the associated sensor's placement and other basic metrics.
        if not msg.payload:
            return
        payload = json.loads(str(msg.payload.decode('utf-8')))
        userdata.sensor_origin = Point(
            payload['origin']['latitude'], payload['origin']['longitude'])
    # Subscribe to the module controls, if the current module is registered to the active (selected) chain
    elif msg.topic == f"Chains/{userdata.chain_uid}/Setup/SubSystems":
        if not msg.payload:
            userdata.is_subsystem_chained = False
            return
        userdata.is_subsystem_chained = userdata.module_uid in json.loads(
            str(msg.payload.decode('utf-8')))
        userdata.is_running = userdata.is_subsystem_chained and userdata.is_chain_running
        userdata.input_channel.status = Status.OPERATIONAL
        userdata.output_channel.status = Status.OPERATIONAL
        if userdata.is_subsystem_chained:
            client.subscribe(
                f"Chains/{userdata.chain_uid}/SubSystems/{userdata.module_uid}/Controls/#")
            client.subscribe(
                f"Chains/{userdata.chain_uid}/SubSystems/{userdata.module_uid}/Data/+/Interpretation")
            client.subscribe(
                f"Chains/{userdata.chain_uid}/SubSystems/{userdata.module_uid}/Incoming")
            client.subscribe(
                f"Chains/{userdata.chain_uid}/SubSystems/{userdata.module_uid}/Outgoing")
            for configured_control in userdata.controls:
                configured_control.reset_force_refresh_time()
            for configured_data_item in userdata.data_items:
                configured_data_item.reset_force_refresh_time()
    # Check if topic exists in configured controls (by UID) and update the locally held details (if true)
    # or remove from the broker by publishing an empty string (if false)
    elif str.startswith(msg.topic, f"Chains/{userdata.chain_uid}/SubSystems/{userdata.module_uid}/Controls"):
        incoming_control_uid = msg.topic[-32:]
        configured_control = next(
            (c for c in userdata.controls if c.uid == incoming_control_uid), None)
        if isinstance(configured_control, Control):
            configured_control.from_input(msg.payload)
        elif msg.payload:
            client.publish(msg.topic, "", retain=True)
    # Check if topic exists in configured data items (by key) and update the locally held details (if true)
    # or remove from the broker by publishing an empty string (if false)
    elif str.startswith(msg.topic, f"Chains/{userdata.chain_uid}/SubSystems/{userdata.module_uid}/Data") and str.endswith(msg.topic, "/Interpretation"):
        incoming_data_key = msg.topic[89:-15]
        configured_data_item = next(
            (d for d in userdata.data_items if d.key == incoming_data_key), None)
        if isinstance(configured_data_item, DataItem):
            configured_data_item.from_input(msg.payload)
        elif msg.payload:
            client.publish(msg.topic, "", retain=True)
    # Define incoming channel details
    elif msg.topic == f"Chains/{userdata.chain_uid}/SubSystems/{userdata.module_uid}/Incoming":
        userdata.input_channel.halt()
        if not msg.payload:
            userdata.input_channel.endpoint = None
        else:
            payload = json.loads(str(msg.payload.decode('utf-8')))
            if payload and payload['protocol']:
                endpoint = Endpoint(
                    payload['protocol'], payload['ip'], payload['port'])
                if "layout" in payload:
                    userdata.input_channel.struct_format = dataTypesToFormat(
                        payload['layout'])
                    userdata.input_channel.struct_size = dataTypesToSize(
                        payload['layout'])
                for key in payload['topics']:
                    userdata.input_channel.stream_key = key
                    topic = f"Chains/{userdata.chain_uid}/SubSystems/{payload['source']}/Data/{key}/Records" if 'source' in payload else key
                    endpoint.topics.append(topic)
                userdata.input_channel.endpoint = endpoint
    # Define outgoing channel details
    elif msg.topic == f"Chains/{userdata.chain_uid}/SubSystems/{userdata.module_uid}/Outgoing":
        userdata.output_channel.halt()
        if not msg.payload:
            userdata.output_channel.endpoint = None
        else:
            payload = json.loads(str(msg.payload.decode('utf-8')))
            if payload and payload['protocol']:
                new_endpoint = Endpoint(
                    payload['protocol'], payload['ip'], payload['port'])
                for key in userdata.output_channel.stream_keys:
                    topic = f"Chains/{userdata.chain_uid}/SubSystems/{userdata.module_uid}/Data/{key}/Records"
                    new_endpoint.topics.append(topic)
                userdata.output_channel.endpoint = new_endpoint


class Controller(Component):
    """ Class providing the necessary logic for the subsystem controller. """

    def __init__(self, context):
        super().__init__()
        self._context = context

    async def loop_async(self):
        """ Initialize the primary MQTT client, and effect the sub-system controller loop """
        client = mqtt.Client(client_id=f"{self._context.module_uid}_control", clean_session=True,
                             userdata=self._context, protocol=mqtt.MQTTv311, transport='tcp')
        if self._context.broker.protocol == Protocol.MQTTS:
            # Enables TLS1.2 with externally provided keys/certificates
            client.tls_set(None, None, None, cert_reqs=ssl.CERT_NONE,
                           tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
            # disables peer verification
            client.tls_insecure_set(True)
        # -------------------------------------------------------------------------
        client.is_connected = False
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        status_loop_counter = 0
        counter = 0
        # -------------------------------------------------------------------------
        print(f"{Style.INFO}MQTT subscriber connecting on {self._context.broker.ip_address}:{self._context.broker.port}{' with TLS support' if self._context.broker.protocol == Protocol.MQTTS else ''}...{Style.EOS}")
        client.connect_async(self._context.broker.ip_address,
                             self._context.broker.port, 60)
        # -------------------------------------------------------------------------
        # Initialize connection to the broker as configured
        client.loop_start()
        # Wait for connection setup to complete
        while not client.is_connected:
            await asyncio.sleep(1)
        # -------------------------------------------------------------------------
        # Non-event driven loop, primarily to allow for publishing of system states on a polled basis
        while self._context.broker.is_active:
            if self._context.is_running:
                if self._context.input_channel.endpoint and not self._context.input_channel.is_started:
                    await self._context.input_channel.start_async()
                if self._context.output_channel.endpoint and not self._context.output_channel.is_started:
                    await self._context.output_channel.start_async()
            else:
                if self._context.input_channel.is_started:
                    await self._context.input_channel.stop_async()
                if self._context.output_channel.is_started:
                    await self._context.output_channel.stop_async()
            # ---------------------------------------------------------------------
            counter = counter + 1
            # ---------------------------------------------------------------------
            # Broadcast availability by publishing label to the "AvailableSubSystems" topic, since this is not
            # considered critical, the topic will only be updated on every fourth iteration of the loop.
            status_loop_counter = (status_loop_counter + 1) % 4
            if not status_loop_counter:
                client.publish(
                    f"AvailableSubSystems/{self._context.module_uid}/Definition",
                    json.dumps({
                        "label": self._context.module_name,
                        "streams": self._context.output_channel.stream_keys}),
                    retain=True)
                # Check that sub-system controls are configured correctly, after a defined timeout elapses
                if self._context.chain_uid and self._context.is_subsystem_chained:
                    topic_prefix = f"Chains/{self._context.chain_uid}/SubSystems/{self._context.module_uid}"
                    for data_item in self._context.data_items:
                        if data_item.needs_initialization():
                            client.publish(
                                f"{topic_prefix}/Data/{data_item.key}/Interpretation",
                                data_item.to_output(), retain=True)
                    for control in self._context.controls:
                        if control.needs_initialization():
                            client.publish(
                                f"{topic_prefix}/Controls/{control.uid}",
                                control.to_output(), retain=True)
            # Publish status of sub-system, as determined from the input, output and process components
            client.publish(
                f"AvailableSubSystems/{self._context.module_uid}/Status",
                await self._context.determine_status())
            # Publish activity info where sub-system is configured to the selected chain
            if self._context.chain_uid:
                # Publish processing and error rates
                if self._context.is_subsystem_chained:
                    client.publish(
                        f"Chains/{self._context.chain_uid}/SubSystems/{self._context.module_uid}/Rates",
                        await self._context.rates_to_output())
            # ---------------------------------------------------------------------
            # Give tardy connection clean-up processes time to complete
            await asyncio.sleep(1)
        # -------------------------------------------------------------------------
        print(f"{Style.INFO}MQTT controller disconnecting...{Style.EOS}")
        client.disconnect()
        client.loop_stop()

    async def start_async(self):
        """ Asynchronously sets the flag that governs ongoing thread loops and creates a new worker thread. """
        if self._is_started or (self._worker and self._worker.is_alive):
            await self.stop_async()
        self._is_started = True
        self._worker = threading.Thread(target=self.loop_process, daemon=True)
        self._worker.start()

    async def stop_async(self):
        """ Asynchronously sets the flag that terminates any ongoing thread loops and joins the worker thread back. """
        self._context.is_running = False
        self._is_started = False
        if self._context.input_channel:
            await self._context.input_channel.shutdown_async()
        if self._context.output_channel:
            await self._context.output_channel.shutdown_async()
        if self._worker:
            self._worker.join(2)
        # try:
        #     await self._context.input_channel.shutdown_async()
        # except:
        #     pass
        # try:
        #     await self._context.output_channel.shutdown_async()
        # except:
        #     pass
        # try:
        #     self._worker.join(1)
        # except:
        #     pass
