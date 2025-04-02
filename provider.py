import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum

import requests

class ProviderType(Enum):
    WUNDERGROUD="wunderground"
    OPENWEATHER="openweather"

class WeatherProvider(ABC):
    def __init__(self, api_key, units):
        self.api_key = api_key
        self.conditions = {"valid": False}
        self.units = units

    @abstractmethod
    def get_weather(self, latitude, longitude):
        pass

class WundergroundProvider(WeatherProvider):
    def __init__(self, api_key, units):
        if units == "metric":
            units = "m"
        elif units == "imperial":
            units = "e"

        super().__init__(api_key, units)
        self.base_url = "https://api.weather.com"

    def get_weather(self, latitude, longitude):
        if self.api_key is None:
            pass
        try:
            response = requests.get(f"{self.base_url}/v3/location/near?geocode={latitude},{longitude}&product=pws&format=json&apiKey={self.api_key}")
            if response.status_code == 200:
                data = response.json()
                city = data["location"]["stationName"][0]
                pws = data["location"]["stationId"][0]

                self.conditions['city'] = city

                response = requests.get(f"{self.base_url}/v2/pws/observations/current?stationId={pws}&format=json&units={self.units}&apiKey={self.api_key}")
                if response.status_code == 200:
                    data = response.json()
                    self.conditions['temperature'] = data["observations"][0]["metric"]["temp"]
                    self.conditions['humidity'] = data["observations"][0]["humidity"]
                    self.conditions['last_update'] = datetime.now()
                    self.conditions['valid'] = True
            else:
                logging.debug("Failed to get weather data: status code is %s" % response.status_code)
                self.conditions['valid'] = False
        except Exception:
            logging.exception("Failed to get weather data")
            self.conditions['valid'] = False


class OpenweatherProvider(WeatherProvider):
    def __init__(self, api_key, units):
        super().__init__(api_key, units)
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

    def get_weather(self, latitude, longitude):
        if self.api_key is None:
            pass
        try:
            response = requests.get(f"{self.base_url}?lat={latitude}&lon={longitude}&units={self.units}&appid={self.api_key}")
            if response.status_code == 200:
                data = response.json()
                city = data["name"]
                self.conditions['city'] = city
                self.conditions['temperature'] = data["main"]["temp"]
                self.conditions['humidity'] = data["main"]["humidity"]
                self.conditions['last_update'] = datetime.now()
                self.conditions['valid'] = True
            else:
                logging.debug("Failed to get weather data: status code is %s" % response.status_code)
                self.conditions['valid'] = False
                self.conditions['valid'] = False
        except Exception:
            logging.exception("Failed to get weather data")
            self.conditions['valid'] = False
