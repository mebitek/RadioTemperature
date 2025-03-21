import configparser
import logging
import os
import shutil

from temperature import Temperature


class AppConfig:
    def __init__(self):
        self.config = configparser.ConfigParser()
        config_file = "%s/../conf/radio_temperature_config.ini" % (os.path.dirname(os.path.realpath(__file__)))
        if not os.path.exists(config_file):
            sample_config_file = "%s/config.sample.ini" % (os.path.dirname(os.path.realpath(__file__)))
            shutil.copy(sample_config_file, config_file)
        self.config.read("%s/../conf/radio_temperature_config.ini" % (os.path.dirname(os.path.realpath(__file__))))

    def get_debug(self):
        val = self.config.get("Setup", "debug", fallback=False)
        if val == "true":
            return True
        else:
            return False

    def get_gps(self):
        return self.config.get("Setup", "gps", fallback="com.victronenergy.gps.ve_ttyACM0")

    def get_mqtt_address(self):
        address = self.config.get('MQTTBroker', 'address', fallback=None)
        if address is None:
            logging.error("No MQTT Broker set in config.ini")
            return address
        else:
            return address

    def get_mqtt_port(self):
        port = self.config.get('MQTTBroker', 'port', fallback=None)
        if port is not None:
            return int(port)
        else:
            return 1883

    def get_mqtt_name(self):
        return self.config.get('MQTTBroker', 'name', fallback='MQTT_to_Inverter')

    def get_online(self):
        return self.config.get('Online', 'addDevice', fallback=False)

    def get_provider(self):
        return self.config.get('Online', 'provider', fallback="wunderground")

    def get_api_key(self):
        return self.config.get('Online', 'apiKey', fallback=False)

    def get_interval(self):
        return int(self.config.get('Online', 'interval', fallback=10))

    def get_units(self):
        units = self.config.get('Online', 'units', fallback="metric")
        if units is not "metric" or units is not "imperial":
            units = "metric"
        return units

    def get_devices(self):
        devices = []
        for key in self.config['Devices']:
            device_info = self.config['Devices'][key].split(',')
            devices.append(Temperature(key, device_info[0], device_info[1], device_info[2], device_info[3], device_info[4], False,0, 0 ))
        return devices


    def write_to_config(self, value, path, key):
        logging.debug("Writing config file %s %s " % (path, key))
        self.config[path][key] = str(value)
        with open("%s/../conf/radio_temperature_config.ini" % (os.path.dirname(os.path.realpath(__file__))), 'w') as configfile:
            self.config.write(configfile)

    @staticmethod
    def get_version():
        with open("%s/version" % (os.path.dirname(os.path.realpath(__file__))), 'r') as file:
            return file.read()
