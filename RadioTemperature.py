#!/usr/bin/env python

import json
import logging
import os
import random
import sys
from datetime import datetime, timedelta

import dbus

import subprocess
import _thread as thread

from dbus import SessionBus, SystemBus, DBusException

from app_config import AppConfig
from mqtt_broker import Broker
from provider import WundergroundProvider, OpenweatherProvider, ProviderType
from temperature import Temperature, TemperatureType

# add the path to our own packages for import
sys.path.insert(1, "/data/SetupHelper/velib_python")

from vedbus import VeDbusService, VeDbusItemImport
from gi.repository import GLib


def dbus_connection():
    return SessionBus(private=True) if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else SystemBus(private=True)


topic_category = {}
instances = {}


class RadioTemperatureService:
    def __init__(self, servicename, deviceinstance, paths, productname='Temperature Radio Sensor', connection='MQTT',
                 config=None, device=None):

        self.config = config or AppConfig()
        # temperature class
        self.temperature = device

        self.dbus_conn = None
        if self.temperature.is_online:
            self.dbus_conn = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()

        # dbus service
        logging.debug("* * * %s" % servicename)
        self.dbusservice = VeDbusService(servicename, bus=dbus_connection(), register=False)
        self._paths = paths

        self.dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self.dbusservice.add_path('/Mgmt/ProcessVersion', self.config.get_version())
        self.dbusservice.add_path('/Mgmt/Connection', connection)

        # Create the mandatory objects
        self.dbusservice.add_path('/DeviceInstance', deviceinstance)
        # value used in ac_sensor_bridge.cpp of dbus-cgwacs
        self.dbusservice.add_path('/ProductId', random.randint(1, 9))
        self.dbusservice.add_path('/ProductName', self.temperature.name)
        self.dbusservice.add_path('/DeviceName', self.temperature.name)
        self.dbusservice.add_path('/FirmwareVersion', 0x0136)
        self.dbusservice.add_path('/HardwareVersion', 8)
        self.dbusservice.add_path('/Connected', 1)
        self.dbusservice.add_path('/Serial', "xxxx")

        for path, settings in self._paths.items():
            self.dbusservice.add_path(
                path, settings['initial'], writeable=True, onchangecallback=self._handlechangedvalue)

        self.dbusservice.register()
        GLib.timeout_add(1000, self._update)

    def _update(self):
        logging.debug("* * * Updating device info")

        if self.temperature.is_online:

            try:
                gps = self.config.get_gps()
                latitude = VeDbusItemImport(self.dbus_conn, gps, '/Position/Latitude')
                longitude = VeDbusItemImport(self.dbus_conn, gps, '/Position/Longitude')
                logging.debug("* * * latitude: %s, longitude: %s" % (latitude, longitude))
            except DBusException as e:
                logging.debug("* * * GPS not connected")
                return True

            if latitude.get_value() is None or longitude.get_value() is None:
                logging.debug("* * * GPS not fixed")
                return True

            if self.temperature.last_update is None or datetime.now() > self.temperature.last_update + timedelta(
                    minutes=self.config.get_interval()):

                if self.config.get_provider() == ProviderType.WUNDERGROUD.value:
                    provider = WundergroundProvider(self.config.get_api_key(), self.config.get_units())
                elif self.config.get_provider() == ProviderType.OPENWEATHER.value:
                    provider = OpenweatherProvider(self.config.get_api_key(), self.config.get_units())
                else:
                    logging.debug("* * * not valid provider.")
                    return True

                provider.get_weather(latitude.get_value(), longitude.get_value())
                conditions = provider.conditions
                if conditions.get("valid"):
                    city = conditions.get("city")
                    self.temperature.name = city
                    self.dbusservice['/CustomName'] = city

                    self.temperature.temperature = conditions.get("temperature")
                    self.temperature.humidity = conditions.get("humidity")
                    self.temperature.last_update = conditions.get("last_update")
                else:
                    logging.debug("* * * not valid weather.")
                    return True
            else:
                logging.debug("* * * Online Device: interval not reached, not updating")

        self.dbusservice['/Temperature'] = self.temperature.temperature
        self.dbusservice['/Humidity'] = self.temperature.humidity


        if self.config.get_aggregate():
            temp = 0
            humidity = 0
            i = 0
            for key, instance in instances.items():
                logging.debug("* * * Instance %s type %d" % (instance.dbusservice.name, instance.temperature.device_type))
                if instance.temperature.device_type == 4 and not instance.temperature.is_aggregate:
                    temp = temp + instance.temperature.temperature
                    humidity = humidity + instance.temperature.humidity
                    i += 1
                    logging.debug("* * * Total of outside instances %d" % i)


            aggregate_instance = instances['aggregate_1']
            aggregate_instance.temperature.temperature = temp / i
            aggregate_instance.temperature.humidity = humidity / i
            aggregate_instance.dbusservice['/Temperature'] = aggregate_instance.temperature.temperature
            aggregate_instance.dbusservice['/Humidity'] = aggregate_instance.temperature.humidity

        index = self.dbusservice['/UpdateIndex'] + 1  # increment index
        if index > 255:  # maximum value of the index
            index = 0  # overflow from 255 to 0
        self.dbusservice['/UpdateIndex'] = index
        return True

    def _handlechangedvalue(self, path, value):
        global instances
        logging.debug("* * * change from outside %s to %s" % (path, value))

        for key in instances:
            instance = instances[key]
            if instance.dbusservice.name == self.dbusservice.name:
                logging.debug("* * * INSTANCE CHANGED %s - %s" % (key, self.dbusservice.name))
                instance.temperature.device_type = value
                instances[key] = self
                break

        return True


def main():
    config = AppConfig()

    # set logging level to include info level entries
    level = logging.INFO
    if config.get_debug():
        level = logging.DEBUG
    logging.basicConfig(level=level)

    logging.info(">>>>>>>>>>>>>>>> Radio Temperature Starting <<<<<<<<<<<<<<<<")

    subprocess.Popen(['/data/RadioTemperature/bin/rtl_433', '-c', "/data/RadioTemperature/bin/rtl.conf"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    thread.daemon = True

    from dbus.mainloop.glib import DBusGMainLoop
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    devices = config.get_devices()
    online = config.get_online()
    aggregate = config.get_aggregate()

    if aggregate and not online:
        aggregate = False

    if online:
        provider = config.get_provider()
        device = Temperature("online", provider, 1, None, None, TemperatureType.OUTDOOR.value, True, 0, 0)
        devices.append(device)

    if aggregate:
        device = Temperature("Outdoor", "aggregate", 1, None, None, TemperatureType.OUTDOOR.value, False, 0, 0)
        device.is_aggregate = True
        devices.append(device)

    broker = Broker(config.get_mqtt_name(), config.get_mqtt_address(), config.get_mqtt_port())
    broker.on_message(on_message)

    for device in devices:
        if not device.is_online and not device.is_aggregate:
            topic_category[device.topic] = device.model

    broker.topic_category = topic_category

    broker.connect_broker()

    i = 0
    for device in devices:
        logging.debug("***** %s " % 'com.victronenergy.temperature.%s' % device.normalize_name())
        logging.debug("***** %d " % device.device_type)
        logging.debug("***** %s " % device.is_online)


        service_name = 'com.victronenergy.temperature.%s' % device.normalize_name()
        vac_output = RadioTemperatureService(
            servicename=service_name,
            deviceinstance=40 + i,
            paths={
                '/Temperature': {'initial': 0},
                '/Humidity': {'initial': 0},
                '/Pressure': {'initial': None},
                '/Status': {'initial': 0},
                '/TemperatureType': {'initial': device.device_type},
                '/CustomName': {'initial': device.normalize_name()},
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
            if 'pressure_hPa' in jsonpayload:
                device.pressure = jsonpayload['pressure_hPa']
        else:
            logging.debug("Topic not in configurd topics. This shouldn't be happen")

    except Exception as e:
        logging.exception("Error in handling of received message payload: " + msg.payload)
        logging.exception(e)


if __name__ == "__main__":
    main()
