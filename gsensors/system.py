#-*- coding:utf-8 -*-
import logging

import psutil
from nut2 import PyNUTClient, PyNUTError

from gsensors import DataSource, AutoUpdateValue

class CpuUsage(AutoUpdateValue):
    unit = "%"
    update_freq = 1.9

    def update(self):
        self.value = psutil.cpu_percent(interval=0)


class NutUPS(AutoUpdateValue):
    """
    Doc des variables:

    http://www.networkupstools.org/docs/developer-guide.chunked/apas01.html
    """
    update_freq = 1.
    DATA_UNITS = {
        'battery_charge': '%',
        'battery_charge_low': '%',
        'battery_charge_warning': '%',
        #'battery_date': 'not set',
        #'battery_mfr_date': '2015/01/27',
        'battery_runtime': 's',
        'battery_runtime_low': 's',
        'battery_type': None,
        'battery_voltage': 'V',
        'battery_voltage_nominal': 'V',
        #'device_mfr': '',
        #'device_model': '',
        #'device_serial': '',
        #'device_type': 'ups',
        #'driver_name': 'usbhid-ups',
        #'driver_parameter_pollfreq': '30',
        #'driver_parameter_pollinterval': '5',
        #'driver_parameter_port': 'auto',
        #'driver_version': None,
        #'driver_version_data': None,
        #'driver_version_internal': None,
        'input_sensitivity': None,
        'input_transfer_high': 'V',
        'input_transfer_low': 'V',
        'input_transfer_reason': None,
        'input_voltage': 'V',
        'input_voltage_nominal': 'V',
        'ups_beeper_status': None,
        'ups_delay_shutdown': 's',
        #'ups_firmware': '',
        #'ups_firmware_aux': '',
        'ups_load': '%',
        #'ups_mfr': '',
        #'ups_mfr_date': '2015/01/27',
        #'ups_model': '',
        #'ups_productid': '',
        #'ups_serial': '5B1505T00878  ',
        'ups_status': None,
        #'ups_timer_reboot': '0',
        #'ups_timer_shutdown': '-1',
        #'ups_vendorid': ''
    }

    def __init__(self, upsname, host="127.0.0.1", port=3493, login=None, password=None):
        super(NutUPS, self).__init__()
        self.upsname = upsname
        self.host = host
        self.port = port
        self.login = login
        self.password = password

        self._sources = {}

    def update(self):
        nut = PyNUTClient(host=self.host, port=self.port, login=self.login, password=self.password)
        # get data
        #TODO: add try catch on it to detect error
        try:
            data = nut.list_vars(self.upsname)
        except PyNUTError as err:
            self._logger.error(err)
            self.error = "Communication error with UPS"
        else:
            for name, source in self._sources.items():
                key = name.replace("_", ".")
                if key in data:
                    source.value = data[key]
                else:
                    self._logger.debug("Missing data: %s" % key)
            #pprint(data)
        del nut #close connection

    def __getattr__(self, value):
        if value not in self.DATA_UNITS:
            raise AttributeError("Unknow data")
        if value not in self._sources:
            _src = DataSource(name=value, unit=self.DATA_UNITS[value])
            self._sources[value] = _src
        return self._sources[value]

