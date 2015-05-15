#-*- coding:utf-8 -*-
""" MQTT sources based on `paho-mqtt`
"""
import logging
from datetime import datetime

import gevent
import gevent.monkey
gevent.monkey.patch_all()   # needed for websocket

import requests
import random
import json

from ws4py.client import WebSocketBaseClient

from gsensors.basic import DataSource


class MFIWebSocketClient(WebSocketBaseClient):
    def __init__(self, mfi_device):
        self.mfi_device = mfi_device
        super(MFIWebSocketClient, self).__init__(self.mfi_url, protocols=['mfi-protocol'])

    @property
    def mfi_url(self):
        return "ws://%s:7681/?c=%s" % (self.mfi_device._host, self.mfi_device._token)

    def handshake_ok(self):
        gevent.spawn(self.run)

    def received_message(self, msg):
        data = json.loads(str(msg))
        self.mfi_device.incoming_ws_data(data)

#    def opened(self):
#        print "opened"
#        #self.send('{"time":3000}')

#    def closed(self, code, reason=None):
#        print "Closed down", code, reason




class MFIDevice(object):
    #doc de l'API:
    # http://community.ubnt.com/t5/mFi/mPower-mFi-Switch-and-mFi-In-Wall-Outlet-HTTP-API/td-p/1076449
    def __init__(self, host):
        self._host = host
        self.running = False
        self._token = None
        self._sources = []

    def register_source(self, source):
        self._sources.append(source)

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

    def login(self, user, password):
        self._token = MFIDevice.random_token()
        print self._token
        data = {
            "username": user,
            "password": password,
        }
        res = requests.post(self.url + "/login.cgi", data, cookies=self.cookies)

    def logout(self):
        requests.get(self.url + "/logout.cgi", cookies=self.cookies)

    def get_json(self):
        res = requests.get(self.url + "/sensors", cookies=self.cookies)
        ## convert to KwH
#		if (row.prevmonth) {
#			row.prevmonth *= 0.0003125;
#		}
#		if (row.thismonth) {
#			row.thismonth *= 0.0003125;
#		}
        return res.json()

    def set_output(self, port, value):
        data = {
            "output": 0 if value in [0, False, "off"] else 1,
        }
        res = requests.post("%s/sensors/%s" % (self.url, port), data, cookies=self.cookies)

    def incoming_ws_data(self, data):
        print("--- WS ---")
        from pprint import pprint
        #pprint(data)

    def incoming_data(self, data):
        print("--- DATA ---")
        from pprint import pprint
        pprint(data)

    def _update(self):
        while True:
            data = self.get_json()
            self.incoming_data(data)
            gevent.sleep(1)

    def start(self):
        ws = MFIWebSocketClient(self)
        gevent.spawn(self._update)
        ws.connect()


def main():
    mpower = MFIDevice("192.168.100.14")
    user = raw_input("login: ")
    password = raw_input("password: ")


    mpower.login(user, password)
    mpower.set_output(6, 1)
    gevent.sleep(1)
    mpower.set_output(6, 0)
    #mpower.start()


    #gevent.wait()
    #mpower.logout()
    #print mpower.get_json()

if __name__ == '__main__':
    import sys
    sys.exit(main())

