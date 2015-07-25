#-*- coding:utf-8 -*-
""" Client for OpenWeatherMap API

See:
* http://openweathermap.org/current

"""
import logging
from time import time
from datetime import datetime

import requests
import gevent

from gsensors import AutoUpdateValue


class OwmClient(object):
    ttl = 10 #10*60 # make a request every 10mins max

    def __init__(self, city):
        self.city = city
        self._data = None
        self._last_update = 0

    @property
    def url(self):
        return "http://api.openweathermap.org/data/2.5/weather?q=%s" % self.city

    @property
    def data(self):
        _last_update = time()
        if self._data is None or abs(_last_update - self._last_update) > self.ttl:
            self._data = self._get_data()
            self._last_update = _last_update
        return self._data

    def _get_data(self):
        raw = requests.get(self.url)
        data = raw.json()
        # ajoute temp in celsius
        data["main"]["celsius"] = data["main"]["temp"] - 273.15
        return data

    @property
    def dt(self):
        return datetime.fromtimestamp(self.data["dt"])


class OwmSource(AutoUpdateValue):
    key = None
    unit = None

    def __init__(self, owm_client, name=None, key=None, unit=None):
        """
        :attr own_client: :class:`OwmClient` instance
        :attr key: key to be show splitted by '/'
        """
        self.owm_client = owm_client
        update_freq = owm_client.ttl
        if key is not None:
          self.key = key
        if unit is not None:
          self.unit = unit
        self.value = None
        super(OwmSource, self).__init__(name=name, unit=self.unit, update_freq=update_freq)

    def update(self):
        value = self.owm_client.data
        for key in self.key.split("/"):
            value = value[key]
        self.set_value(value, self.owm_client.dt)

class OwmTemp(OwmSource):
    unit = "°C"
    key = "main/celsius"  #NOTE: this key is added by OwmClient !

class OwmHumidity(OwmSource):
    unit = "%"
    key = "main/humidity"

class OwmPressure(OwmSource):
    unit = "hPa"
    key = "main/pressure"

class OwmClouds(OwmSource):
    unit = "%"
    key = "clouds/all"



