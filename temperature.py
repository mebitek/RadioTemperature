import re
from enum import Enum


class TemperatureType(Enum):
    BATTERY=0
    FRIDGE=1
    GENERIC=2
    ROOM=3
    OUTDOOR=4
    WATER_HEATER=5
    FREEZER=6

class Temperature:
    def __init__(self, name, model, channel, topic, temperature_json_field, device_type, temperature, humidity ):
        self.name = name
        self.model = model
        self.channel = channel
        self.topic = topic
        self.temperature_json_field = temperature_json_field
        self.device_type = device_type

        self.temperature = temperature
        self.humidity = humidity

    def normalize_name(self):
        return re.sub(r'[^a-zA-Z0-9]', '_', self.name)