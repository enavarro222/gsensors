#-*- coding:utf-8 -*-
import sys
import struct
import array, io, fcntl

import smbus

from gevent import sleep
from gsensors import AutoUpdateValue, DataSource


class I2CRaw(object):
    def __init__(self, device, bus):
        self.fr = io.open("/dev/i2c-"+str(bus), "rb", buffering=0)
        self.fw = io.open("/dev/i2c-"+str(bus), "wb", buffering=0)

        # set device address
        I2C_SLAVE=0x0703
        fcntl.ioctl(self.fr, I2C_SLAVE, device)
        fcntl.ioctl(self.fw, I2C_SLAVE, device)

    def write(self, bytes):
        self.fw.write(bytes)

    def read(self, bytes):
        return self.fr.read(bytes)

    def close(self):
        self.fw.close()
        self.fr.close()


class I2CBus():
    def __init__(self, i2c_slave, i2c_bus=0):
        self._bus = smbus.SMBus(i2c_bus)
        self._i2c_slave = i2c_slave
        #TODO: check i2c device exist

    def read_block(self, cmd, nb_bytes):
        bytes = self._bus.read_i2c_block_data(self._i2c_slave, cmd, nb_bytes)
        return bytes

    def read_byte(self, cmd):
        result = self._bus.read_byte_data(self._i2c_slave, cmd)
        return result

    def read_cast(self, cmd, nb_bytes=4, cast="f"):
        """
        to see all possible cast:
        http://docs.python.org/2/library/struct.html#format-characters
        """
        bytes = self.read_block(cmd, nb_bytes=nb_bytes)
        return struct.unpack(cast, "".join(map(chr, bytes)))[0]

    def read_float(self, cmd):
        return self.read_cast(cmd, 4, "f")

    def read_long(self, cmd):
        return self.read_cast(cmd, 4, "l")

    def read_unsigned_long(self, cmd):
        return self.read_cast(cmd, 4, "l")


class BMP085(AutoUpdateValue):
    """ interface for pressure mesurement with an I2C BMP085 sensor

    depend on adafruit code:
    https://github.com/adafruit/Adafruit_Python_BMP
    """
    update_freq = 30

    def __init__(self, name=None):
        AutoUpdateValue.__init__(self, name=name)
        from Adafruit_BMP import BMP085
        self.bmp = BMP085.BMP085()
        self._temp = None
        self._pressure = None

    @property
    def temp(self):
        if self._temp is None:
            name = "%s.temp" % self.__class__.__name__
            self._temp = DataSource(name=name, unit="°C", timeout=None)
        return self._temp

    @property
    def pressure(self):
        if self._pressure is None:
            name = "%s.temp" % self.__class__.__name__
            self._pressure = DataSource(name=name, unit="hPa", timeout=None)
        return self._pressure

    def update(self):
        if self._temp:
            self._temp.value = self.bmp.read_temperature()
        if self._pressure:
            self._pressure.value = self.bmp.read_pressure()


class LightBH1750(AutoUpdateValue):
    """ interface for an I2C BH1750 light sensor
    """
    update_freq = 30
    unit = "lx"

    def __init__(self, i2c_bus=1, name=None):
        AutoUpdateValue.__init__(self, name=name)
        self.device_addr = 0x23
        self._bus = I2CBus(i2c_slave=self.device_addr, i2c_bus=i2c_bus)

    def update(self):
        val = self._bus.read_cast(0x21, 2, ">H") / 1.2
        self.set_value(val)


class HTU21D(AutoUpdateValue):
    #cf https://www.raspberrypi.org/forums/viewtopic.php?f=32&t=84966
    update_freq = 30

    # HTU21D Address
    device_addr = 0x40
    # Commands
    CMD_READ_TEMP_HOLD = "\xE3"
    CMD_READ_HUM_HOLD = "\xE5"
    CMD_READ_TEMP_NOHOLD = "\xF3"
    CMD_READ_HUM_NOHOLD = "\xF5"
    CMD_WRITE_USER_REG = "\xE6"
    CMD_READ_USER_REG = "\xE7"
    CMD_SOFT_RESET= "\xFE"

    def __init__(self, i2c_bus=1, name=None):
        AutoUpdateValue.__init__(self, name=name)
        self.dev = I2CRaw(device=self.device_addr, bus=i2c_bus)
        self._temp = None
        self._hum = None
        self.dev.write(self.CMD_SOFT_RESET) #soft reset
        sleep(.1)

    def update(self):
        if self._temp:
            self._temp.value = self.read_temp()
        if self._hum:
            if self._temp:
                sleep(.2)
            self._hum.value = self.read_hum()

    @property
    def temp(self):
        if self._temp is None:
            name = "%s.temp" % self.__class__.__name__
            self._temp = DataSource(name=name, unit="°C", timeout=None)
        return self._temp

    @property
    def hum(self):
        if self._hum is None:
            name = "%s.hum" % self.__class__.__name__
            self._hum = DataSource(name=name, unit="%", timeout=None)
        return self._hum

    def ctemp(self, sensorTemp):
        tSensorTemp = sensorTemp / 65536.0
        return -46.85 + (175.72 * tSensorTemp)

    def chumid(self, sensorHumid):
        tSensorHumid = sensorHumid / 65536.0
        return -6.0 + (125.0 * tSensorHumid)

    def crc8check(self, value):
        # Ported from Sparkfun Arduino HTU21D Library: https://github.com/sparkfun/HTU21D_Breakout
        remainder = ( ( value[0] << 8 ) + value[1] ) << 8
        remainder |= value[2]
        
        # POLYNOMIAL = 0x0131 = x^8 + x^5 + x^4 + 1
        # divsor = 0x988000 is the 0x0131 polynomial shifted to farthest left of three bytes
        divsor = 0x988000
        
        for i in range(0, 16):
            if( remainder & 1 << (23 - i) ):
                remainder ^= divsor
            divsor = divsor >> 1
        
        return remainder == 0

    def read_temp(self):
        self.dev.write(self.CMD_READ_TEMP_NOHOLD) #measure temp
        sleep(.1)
        data = self.dev.read(3)
        buf = array.array('B', data)

        if not self.crc8check(buf):
            raise ValueError("Invalid reading")

        temp = (buf[0] << 8 | buf [1]) & 0xFFFC
        return self.ctemp(temp)

    def read_hum(self):
        self.dev.write(self.CMD_READ_HUM_NOHOLD) #measure humidity
        sleep(.1)
        data = self.dev.read(3)
        buf = array.array('B', data)
        
        if not self.crc8check(buf):
            raise ValueError("Invalid reading")

        humid = (buf[0] << 8 | buf [1]) & 0xFFFC
        return self.chumid(humid)

