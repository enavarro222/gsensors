#-*- coding:utf-8 -*-
""" Data source for CurrentCost Serial (ENVI)
"""
import logging
from datetime import datetime

import gevent
import serial
import xmltodict

from gsensors.basic import DataSource


class CurrentcostSerial(object):
    def __init__(self, serial_dev, **kwargs):
        self._serial_dev = serial_dev
        self._ser = None
        self._sources = []
        self.running = False

    def get_data(self, data):
        for source in self._sources:
            source.update(data)

    def register_source(self, source):
        self._sources.append(source)

    def start(self):
        if self.running:
            return
        self.running = True
        self.worker = gevent.spawn(self._loop)

    def _loop(self):
        self._ser = serial.Serial(self._serial_dev, 57600)
        try:
            while True:
                #print("CC loop")
                if self._ser.inWaiting() > 0:
                    data = self._ser.readline().strip()
                    ## remove "empty" char
                    data = data.replace("\x00", "")
                    data = xmltodict.parse(data)
                    self.get_data(data)
                gevent.sleep(0.5)
        finally:
            self._ser.close()


class CurrentcostSource(DataSource):
    def __init__(self, cc, name=None, unit=None):
        super(CurrentcostSource, self).__init__(name=name, unit=unit)
        self._cc = cc
        self._cc.register_source(self)
        self.error = "No data"

    def update(self, data):
        pass

    def start(self):
        # start client (if needed)
        self._cc.start()


class CurrentcostWatts(CurrentcostSource):

    def __init__(self, cc, name=None):
        super(CurrentcostWatts, self).__init__(cc, name=name, unit="W")

    def update(self, data):
        data = data.get("msg", {}).get("ch1", {}).get("watts", None)
        self._logger.info("%s: get data (%s)" % (self.name, data))
        try:
            self.value = int(data)
            self.error = ""
        except ValueError:
            self.error = "Invalid data"
        except:
            self.error = "Unknow error"
        self.changed()


class CurrentcostTemp(CurrentcostSource):

    def __init__(self, cc, name=None):
        super(CurrentcostTemp, self).__init__(cc, name=name, unit="°C")

    def update(self, data):
        data = data.get("msg", {}).get("tmpr", None)
        self._logger.info("%s: get data (%s)" % (self.name, data))
        try:
            self.value = float(data)
            self.error = ""
        except ValueError:
            self.error = "Invalid data"
        except:
            self.error = "Unknow error"
        self.changed()


def main():
    def change_callback(src):
        print("%s: %s %s" % (src.name, src.value, src.error))

    cc = CurrentcostSerial("/dev/ttyUSB0")

    cc_watts = CurrentcostWatts(cc)
    cc_watts.on_change(change_callback)

    cc_temp = CurrentcostTemp(cc)
    cc_temp.on_change(change_callback)

    cc_watts.start()
    cc_temp.start()

    gevent.wait()

if __name__ == '__main__':
    import sys
    sys.exit(main())

