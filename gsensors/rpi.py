#-*- coding:utf-8 -*-
""" Drivers for common sensors on a rPi
"""
import sys
from subprocess import PIPE, Popen

import gevent

from gsensors import AutoUpdateValue


class PiCPUTemp(AutoUpdateValue):
    unit = "°C"
    update_freq = 60

    def update(self):
        process = Popen(['/opt/vc/bin/vcgencmd', 'measure_temp'], stdout=PIPE)
        output, _error = process.communicate()
        self.value = float(output[output.index('=') + 1:output.rindex("'")])


class DHTTemp(AutoUpdateValue):
    def __init__(self, pin, stype="2302", name=None):
        update_freq = 10 #seconds
        super(DHTTemp, self).__init__(name=name, unit="°C", update_freq=update_freq)
        import Adafruit_DHT
        self.Adafruit_DHT = Adafruit_DHT #XXX:mv dans un module a part pour éviter import merdique ici
        TYPES = {
            '11': Adafruit_DHT.DHT11,
            '22': Adafruit_DHT.DHT22,
            '2302': Adafruit_DHT.AM2302
        }
        self.sensor = TYPES.get(stype, stype) #TODO: check stype
        self.pin = pin

    def update(self):
        humidity, temperature = self.Adafruit_DHT.read_retry(self.sensor, self.pin)
        self.value = temperature


def main():
    sources = [
        DHTTemp(18, "22"),
    ]

    def change_callback(src):
        print("%s: %s %s" % (src.name, src.value, src.unit))

    # plug change callback
    for src in sources:
        src.on_change(change_callback)

    for src in sources:
        src.start()

    gevent.wait()

if __name__ == '__main__':
    sys.exit(main())


