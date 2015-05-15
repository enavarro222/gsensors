#-*- coding:utf-8 -*-
""" MQTT sources based on `paho-mqtt`
"""
import logging
from datetime import datetime

import gevent
from paho.mqtt.client import Client

from gsensors.basic import DataSource

class PipaMQTTClient(object): 

    def __init__(self, host, port=1883, **kwargs):
        self._host = host
        self._port = port
        self._mqtt_client = Client()
        self._mqtt_client.on_connect = self.on_connect
        self._mqtt_client.on_message = self.on_message
        self.worker = None
        self.topics_sources = {}
        self.running = False

    def publish(self, topic, payload=None, qos=0, retain=False):
        self._mqtt_client.publish(topic, payload=payload, qos=qos, retain=retain)

    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code "+str(rc))
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        #client.subscribe("$SYS/#")
        #client.subscribe("#")
        for topic in self.topics_sources.keys():
            client.subscribe(topic)

    def on_message(self, client, userdata, msg):
        #print("%s: %s" % (msg.topic, msg.payload))
        if msg.topic in self.topics_sources:
            source = self.topics_sources[msg.topic]
            source.update(msg)

    def register_source(self, source, topic):
        # check that topic has no wildcard
        assert "#" not in topic
        if topic in self.topics_sources:
            raise ValueError("topic already monitored")
        self.topics_sources[topic] = source
        self._mqtt_client.subscribe(topic)
        return source

    def start(self):
        if self.running:
            return
        self.running = True
        self._mqtt_client.connect(host=self._host, port=self._port, keepalive=60)
        self.worker = gevent.spawn(self._mqtt_loop)

    def _mqtt_loop(self):
        while True:
            #print("mqqt loop")
            self._mqtt_client.loop(timeout=.3)
            gevent.sleep(0.6)


class MQTTSource(DataSource):
    """ MQTT source for integer data
    """
    def __init__(self, mqtt_client, topic, name, unit=None):
        super(MQTTSource, self).__init__(name=name, unit=unit)
        self.mqtt_client = mqtt_client
        self.mqtt_client.register_source(self, topic=topic)
        self.error = "No data"

    def update(self, msg):
        self._logger.info("%s: get data (%s)" % (self.name, msg.payload))
        try:
            self.value = self.parse_msg(msg)
            self.error = ""
        except ValueError:
            self.error = "Invalid data"
        except:
            self.error = "Unknow error"
        self.changed()

    def start(self):
        # start client (if needed)
        self.mqtt_client.start()

    def parse_msg(self, msg):
        return msg.payload


class IntSource(MQTTSource):
    """ MQTT source for integer data
    """
    def parse_msg(self, msg):
        return int(msg.payload)

class FloatSource(MQTTSource):
    """ MQTT source for flaot data
    """
    def parse_msg(self, msg):
        return float(msg.payload)

