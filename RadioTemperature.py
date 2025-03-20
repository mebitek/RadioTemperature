#!/usr/bin/env python

import json
import logging
import os
import random
import sys
import threading

import dbus

import subprocess
import _thread as thread

from dbus import SessionBus, SystemBus

from app_config import AppConfig
from mqtt_broker import Broker

# add the path to our own packages for import
sys.path.insert(1, "/data/SetupHelper/velib_python")

from vedbus import VeDbusService
from gi.repository import GLib

def dbus_connection():
    return SessionBus(private=True) if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else SystemBus(private=True)

topic_category = {}
instances = {}

class RadioTemperatureService:
    def __init__(self, servicename, deviceinstance, paths, productname='Temperature Radio Sensor', connection='MQTT',
                 config=None, device=None):

        self.config = config or AppConfig()
        #temperature class
        self.temperature = device

        # dbus service
        logging.debug("* * * %s"%servicename)
        self._dbusservice = VeDbusService(servicename, bus=dbus_connection(), register=False )
        self._paths = paths

        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path('/Mgmt/ProcessVersion', self.config.get_version())
        self._dbusservice.add_path('/Mgmt/Connection', connection)

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', deviceinstance)
        # value used in ac_sensor_bridge.cpp of dbus-cgwacs
        self._dbusservice.add_path('/ProductId', random.randint(1, 9))
        self._dbusservice.add_path('/ProductName', self.temperature.name)
        self._dbusservice.add_path('/DeviceName', self.temperature.name)
        self._dbusservice.add_path('/FirmwareVersion', 0x0136)
        self._dbusservice.add_path('/HardwareVersion', 8)
        self._dbusservice.add_path('/Connected', 1)
        self._dbusservice.add_path('/Serial', "xxxx")

        for path, settings in self._paths.items():
            self._dbusservice.add_path(
                path, settings['initial'], writeable=True, onchangecallback=self._handlechangedvalue)

        self._dbusservice.register()
        GLib.timeout_add(1000, self._update)

    def on_message(self, client, userdata, msg):
        try:
            logging.debug('* * * Incoming message from: ' + msg.topic)

            # write the values into dict
            if msg.topic in self.topic_category:
                jsonpayload = json.loads(msg.payload)
                self.temperature.temperature = jsonpayload[self.temperature.temperature_json_field]
                self.temperature.humidity = jsonpayload['humidity']
            else:
                logging.debug("Topic not in configurd topics. This shouldn't be happen")

        except Exception as e:
            logging.exception("Error in handling of received message payload: " + msg.payload)
            logging.exception(e)

    def _update(self):
        self._dbusservice['/Temperature'] = self.temperature.temperature
        self._dbusservice['/Humidity'] = self.temperature.humidity
        return True

    def _handlechangedvalue(self, path, value):
        return True

def main():

    config = AppConfig()

    # set logging level to include info level entries
    level = logging.INFO
    if config.get_debug():
        level = logging.DEBUG
    logging.basicConfig(level=level)

    logging.info(">>>>>>>>>>>>>>>> Radio Temperature Starting <<<<<<<<<<<<<<<<")

    rtl_process = subprocess.Popen(['/data/RadioTemperature/bin/rtl_433', '-c', "/data/RadioTemperature/bin/rtl.conf"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    thread.daemon = True

    from dbus.mainloop.glib import DBusGMainLoop
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    devices = config.get_devices()


    broker = Broker(config.get_mqtt_name(), config.get_mqtt_address(), config.get_mqtt_port())
    broker.on_message(on_message)

    for device in devices:
        topic_category[device.topic] = device.model

    broker.topic_category = topic_category

    broker.connect_broker()

    i = 0
    for device in devices:

        logging.debug("***** %s " % 'com.victronenergy.temperature.%s'%device.normalize_name())

        vac_output = RadioTemperatureService(
            servicename='com.victronenergy.temperature.%s'%device.normalize_name(),
            deviceinstance=40+i,
            paths={
                '/Temperature': {'initial': 0},
                '/Humidity': {'initial': 0},
                '/TemperatureType': {'initial': device.device_type},
                '/UpdateIndex': {'initial': 0},
            },
            config=config,
            device=device
        )
        instances[f'{device.model}_{device.channel}'] = vac_output
        i = i + 1


    logging.info('Connected to dbus, and switching over to GLib.MainLoop() (= event based)')
    mainloop = GLib.MainLoop()
    mainloop.run()

def on_message(client, userdata, msg):
    try:
        logging.debug('* * * Incoming message from: ' + msg.topic)
        if msg.topic in topic_category:
            jsonpayload = json.loads(msg.payload)

            instance = instances[f'{jsonpayload["model"]}_{jsonpayload["channel"]}']
            device = instance.temperature

            device.temperature = jsonpayload[device.temperature_json_field]
            device.humidity = jsonpayload['humidity']
        else:
            logging.debug("Topic not in configurd topics. This shouldn't be happen")

    except Exception as e:
        logging.exception("Error in handling of received message payload: " + msg.payload)
        logging.exception(e)

if __name__ == "__main__":
    main()