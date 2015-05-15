#-*- coding:utf-8 -*-
import logging
from time import time
from datetime import datetime

import requests
import gevent

from gsensors import AutoUpdateValue

class OwmClient(object):
    ttl = 10*60 # make a request every 10mins max

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
    def __init__(self, name, owm_client, key, unit=""):
        """
        :attr own_client: :class:`OwnClient` instance
        :attr key: key to be show splitted by '/'
        """
        self.owm_client = owm_client
        update_freq = owm_client.ttl
        self.key = key
        self.value = None
        super(OwmSource, self).__init__(name=name, unit=unit, update_freq=update_freq)

    def update(self):
        value = self.owm_client.data
        for key in self.key.split("/"):
            value = value[key]
        self.value = value
        return self.owm_client.dt



