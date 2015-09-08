#-*- coding:utf-8 -*-
""" Data sources for MFI (ubuquity) devices
"""
import logging
from time import time
from datetime import datetime

from collections import defaultdict

import gevent
import gevent.monkey
gevent.monkey.patch_all()   # needed for websocket

import random
import json

import requests
from requests.exceptions import TooManyRedirects

from ws4py.client import WebSocketBaseClient

from gsensors.basic import DataSource
from gsensors.utils import full_exc_info


class MFIConnectionError(RuntimeError):
    pass

class MFIWebSocketClient(WebSocketBaseClient):
    def __init__(self, mfi_device):
        self._logger = logging.getLogger("gsensors.mfi.MFIWebSocketClient")
        self.mfi_device = mfi_device
        super(MFIWebSocketClient, self).__init__(self.mfi_url, protocols=['mfi-protocol'])

    @property
    def mfi_url(self):
        return "ws://%s:7681/?c=%s" % (self.mfi_device._host, self.mfi_device._token)

    def handshake_ok(self):
        gevent.spawn(self.run)

    def closed(self, code, reason=None):
        self._logger.warning("connection closed (%s - %s)" % (code, reason))

    def received_message(self, msg):
        try:
            data = json.loads(str(msg))
            self.mfi_device.incoming_ws_data(data)
        except ValueError as err:
          self._logger.error(err)

#    def opened(self):
#        print "opened"
#        #self.send('{"time":3000}')

#    def closed(self, code, reason=None):
#        print "Closed down", code, reason



class MFIDevice(object):

    get_update_freq = 15 # Update data with a full HTTP GET every... (in seconds)

    #doc de l'API:
    # http://community.ubnt.com/t5/mFi/mPower-mFi-Switch-and-mFi-In-Wall-Outlet-HTTP-API/td-p/1076449
    def __init__(self, host, user, password):
        self._logger = logging.getLogger("gsensors.mfi.MFIDevice")
        self._host = host
        self._user = user
        self._password = password
        self.running = False
        self._token = None
        self._sources = defaultdict(list)
        self.data_sensors = {}
        self.login()

    def register_source(self, port, source):
        self._sources[port].append(source)

    @property
    def url(self):
        return "http://%s" % (self._host)

    @property
    def cookies(self):
        cookies = {
            "AIROS_SESSIONID": self._token,
        }
        return cookies

    @staticmethod
    def random_token():
       return ''.join(random.choice('0123456789abcdef') for x in range(32))

    def login(self):
        self._logger.debug("Login with username: %s" % self._user)
        self._token = MFIDevice.random_token()
        data = {
            "username": self._user,
            "password": self._password,
        }
        res = requests.post(self.url + "/login.cgi", data, cookies=self.cookies)

    def logout(self):
        requests.get(self.url + "/logout.cgi", cookies=self.cookies)

    def get_json(self):
        try:
            res = requests.get(self.url + "/sensors", cookies=self.cookies, timeout=3)
        except TooManyRedirects:
            raise MFIConnectionError()
        ## convert to KwH
        #		if (row.prevmonth) {
        #			row.prevmonth *= 0.0003125;
        #		}
        #		if (row.thismonth) {
        #			row.thismonth *= 0.0003125;
        #		}
        ##
        #TODO: try a better way to check connection
        try:
            result = res.json()
        except ValueError:
            raise MFIConnectionError()
        return result

    def get_output(self, port):
        #data = self.get_json()
        #XXX check if port exist
        return self.data_sensors[port]["output"]

    def set_output(self, port, value):
        data = {
            "output": 0 if value in [0, False, "off"] else 1,
        }
        res = requests.post("%s/sensors/%s" % (self.url, port), data, cookies=self.cookies)

    def SwitchAction(self, port):
        def _action(*args, **kwargs):
            value = not self.get_output(port)
            self.set_output(port, value)
        return _action

    def SwitchOnAction(self, port):
        def _action(*args, **kwargs):
            value = not self.get_output(port)
            self.set_output(port, True)
        return _action

    def SwitchOffAction(self, port):
        def _action(*args, **kwargs):
            self.set_output(port, False)
        return _action

    def incoming_ws_data(self, data):
        data["_source"] = "ws"  #indicate it come's from web socket
        self._incoming_data(data)

    def incoming_data(self, data):
        data["_source"] = "get"  #indicate it come's from http GRY
        self._incoming_data(data)

    def _incoming_data(self, data):
        ports = [(sensor["port"], sensor) for sensor in data["sensors"]]
        for port, sensor_values in ports:
            if port in self.data_sensors:
                self.data_sensors[port].update(sensor_values)
            else:
                self.data_sensors[port] = sensor_values
            for source in self._sources[port]:
                _data = {}
                _data["_source"] = data["_source"]
                _data["sensor"] = sensor_values
                source.update(_data)

    def _update(self):
        ws = MFIWebSocketClient(self)
        ws.connect()
        while True:
            sleep_time = self.get_update_freq
            begin_at = time()
            try:
                data = self.get_json()
                self.incoming_data(data)
            except MFIConnectionError:
                self._logger.warning("connection error")
                # reconnect
                ws.close()
                self.login()
                ws = MFIWebSocketClient(self)
                ws.connect()
                sleep_time = .05 # retry quickly
            except Exception as err:
                #TODO indicate error to sources
                #self._logger.error("update error: %s" % err)
                self._logger.error("update error: %s" % err, exc_info=full_exc_info())
            self._logger.debug("GET updated in %1.2fsec" % (time()-begin_at))
            sleep_time = max(0.01, sleep_time - (time()-begin_at))
            gevent.sleep(sleep_time)

    def start(self):
        if not self.running:
          gevent.spawn(self._update)
          self.running = True


class MFISource(DataSource):
    """ Data Source from MFI device
    """
    def __init__(self, mfi_device, port, name=None, unit=None, timeout=None):
        super(MFISource, self).__init__(name=name, unit=unit, timeout=timeout)
        self.mfi_device = mfi_device
        self.port = port
        self.mfi_device.register_source(self.port, self)
        self.error = "No data"

    def start(self):
        self.mfi_device.start()

    def update(self, data):
        self._logger.info("%s: get data (%s)" % (self.name, data["_source"]))
        #For now only keep WS data
        if data["_source"] != "ws":
            return
        try:
            self.value = self.parse_data(data)
            self.error = None
        except KeyError, ValueError:
            self.error = "Invalid data"
        except:
            self.error = "Unknow error"

    def start(self):
        # start client (if needed)
        self.mfi_device.start()

    def parse_data(self, data):
        """ Should be overriden
        """
        return data


class MFIPower(MFISource):
    def parse_data(self, data):
        return data["sensor"]["power"]

class MFIPowerFactor(MFISource):
    def parse_data(self, data):
        return data["sensor"]["powerfacor"]

class MFIVoltage(MFISource):
    def parse_data(self, data):
        return data["sensor"]["voltage"]

class MFIOutput(MFISource):
    def parse_data(self, data):
        return data["sensor"]["output"]



def main():
    mpower = MFIDevice("192.168.100.13")
    user = raw_input("login: ")
    password = raw_input("password: ")

    mpower.login(user, password)

    sources = [
      MFIPower(mpower, port=1),
      MFIOutput(mpower, port=1)
    ]

    def change_callback(src):
        print("%s:%s" % (src.name, src.value))

    # plug change callback
    for src in sources:
        src.on_change(change_callback)

    for src in sources:
        src.start()

    gevent.wait()



if __name__ == '__main__':
    ## logger
    level = logging.DEBUG
    logger = logging.getLogger("gsensors")
    logger.setLevel(level)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(level)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)

    import sys
    sys.exit(main())

