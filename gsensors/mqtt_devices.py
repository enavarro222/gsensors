#!/usr/bin/env python
#-*- coding:utf-8 -*-
import sys
from time import sleep

from gsensors.mqtt import MQTTSource, IntSource, FloatSource

class MQTTDevice(object):
    def __init__(self, mqtt_client, prefix):
        self._mqtt_client = mqtt_client
        self.prefix = prefix

    def _publish(self, topic, msg):
        self._mqtt_client.publish(self.prefix + topic, msg)

    def start(self):
        self._mqtt_client.start()


class EspSound(MQTTDevice):
    NOTES = { # from https://www.arduino.cc/en/Tutorial/toneMelody
        "B0": 31,
        "C1": 33,
        "CS1": 35,
        "D1": 37,
        "DS1": 39,
        "E1": 41,
        "F1": 44,
        "FS1": 46,
        "G1": 49,
        "GS1": 52,
        "A1": 55,
        "AS1": 58,
        "B1": 62,
        "C2": 65,
        "CS2": 69,
        "D2": 73,
        "DS2": 78,
        "E2": 82,
        "F2": 87,
        "FS2": 93,
        "G2": 98,
        "GS2": 104,
        "A2": 110,
        "AS2": 117,
        "B2": 123,
        "C3": 131,
        "CS3": 139,
        "D3": 147,
        "DS3": 156,
        "E3": 165,
        "F3": 175,
        "FS3": 185,
        "G3": 196,
        "GS3": 208,
        "A3": 220,
        "AS3": 233,
        "B3": 247,
        "C4": 262,
        "CS4": 277,
        "D4": 294,
        "DS4": 311,
        "E4": 330,
        "F4": 349,
        "FS4": 370,
        "G4": 392,
        "GS4": 415,
        "A4": 440,
        "AS4": 466,
        "B4": 494,
        "C5": 523,
        "CS5": 554,
        "D5": 587,
        "DS5": 622,
        "E5": 659,
        "F5": 698,
        "FS5": 740,
        "G5": 784,
        "GS5": 831,
        "A5": 880,
        "AS5": 932,
        "B5": 988,
        "C6": 1047,
        "CS6": 1109,
        "D6": 1175,
        "DS6": 1245,
        "E6": 1319,
        "F6": 1397,
        "FS6": 1480,
        "G6": 1568,
        "GS6": 1661,
        "A6": 1760,
        "AS6": 1865,
        "B6": 1976,
        "C7": 2093,
        "CS7": 2217,
        "D7": 2349,
        "DS7": 2489,
        "E7": 2637,
        "F7": 2794,
        "FS7": 2960,
        "G7": 3136,
        "GS7": 3322,
        "A7": 3520,
        "AS7": 3729,
        "B7": 3951,
        "C8": 4186,
        "CS8": 4435,
        "D8": 4699,
        "DS8": 4978,
    }

    def tune_play(self, note, duration, force=False):
        if note in self.NOTES:
            note = self.NOTES[note]
        self._publish("tune/play", "%s-%s%s" % (note, duration, "-1" if force else ""))

    def tune_stop(self):
        self._publish("tune/stop")


class EspLamp(MQTTDevice):
    def __init__(self, mqtt_client, prefix="esplamp0/"):
        super(EspLamp, self).__init__(mqtt_client, prefix=prefix)
        #self._pressed = MQTTSource(self._mqtt_client, topic=self.prefix + "key/pressed")
        #self._pressed.on_update(self.on_pressed)

    def on(self):
        self._publish("on", "ON")

    def off(self):
        self._publish("off", "OFF")

    def switch(self):
        self._publish("switch", "SWITCH")

    def color(self, led, color):
        self._publish("set/%s" % (led+1), color)

    def color_all(self, color):
        self._publish("set/_all", color)

    def color_full(self, colors):
        self._publish("set/_full", "".join(colors))


class EspLampWithSound(EspLamp, EspSound):
    pass


class LampChevet(EspLampWithSound):
    NB_LEDS = 17
    leds_by_level = [
      [0, 8, 9, 16],
      [1, 7, 10, 15],
      [2, 6, 11, 14],
      [3, 5, 12, 13, 4],
    ]
    leds_by_direction = [
      [0, 1, 2, 3],
      [9, 10, 11, 12],
      [8, 7, 6, 5],
      [16, 15, 14, 13],
    ]

    def __init__(self, mqtt_client, prefix="sys/mclavier/"):
        super(LampChevet, self).__init__(mqtt_client, prefix=prefix)
        # sources
        self.signal = IntSource(self._mqtt_client, topic=self.prefix + "info/signal")
        self.vcc = IntSource(self._mqtt_client, topic=self.prefix + "info/vcc")
        self.in_temp = FloatSource(self._mqtt_client, topic=self.prefix + "temp/1")
        self.out_temp = FloatSource(self._mqtt_client, topic=self.prefix + "temp/0")

    def gauge(self, level, color_on="FF00BB", color_off="000010"):
        colors = {}
        for led_level, leds in enumerate(self.leds_by_level):
            for led in leds:
                if led_level < level:
                   colors[led] = color_on
                else:
                   colors[led] = color_off
        self.color_full([colors[led] for led in range(self.NB_LEDS)])


class MClavier(EspSound):
    KEY2NOTE = [
        ("RED", "C"),
        ("ORANGE", "D"),
        ("YELLOW", "E"),
        ("LIGHT_GREEN", "F"),
        ("DARK_GREEN", "G"),
        ("BLUE", "A"),
        ("PURPLE", "B"),
        ("PINK", "C"),
    ]

    KEY2COLOR = {
        "RED": "173,0,3",
        "ORANGE": "132,27,0",
        "YELLOW": "212,120,0",
        "LIGHT_GREEN": "10,181,0",
        "DARK_GREEN": "38,81,0",
        "BLUE": "0,18,237",
        "PURPLE": "181,0,227",
        "PINK": "235,0,140",
    }

    def __init__(self, mqtt_client, prefix="sys/mclavier/"):
        super(MClavier, self).__init__(mqtt_client, prefix=prefix)
        # convertion helper
        self._key2note = dict(self.KEY2NOTE)
        self._note2key = {note: key for key, note in self.KEY2NOTE[:-1]} #Skip last one
        self._key2pos =  {key: num for num, (key, _) in enumerate(self.KEY2NOTE)}
        # sources
        self.signal = IntSource(self._mqtt_client, topic=self.prefix + "info/signal")
        self.battery = IntSource(self._mqtt_client, topic=self.prefix + "info/battery")
        self._pressed = MQTTSource(self._mqtt_client, topic=self.prefix + "key/pressed")
        self._released = MQTTSource(self._mqtt_client, topic=self.prefix + "key/released")
        self._hold = MQTTSource(self._mqtt_client, topic=self.prefix + "key/hold")
        # Bind events
        self._pressed.on_update(self.on_pressed)
        self._released.on_update(self.on_released)
        self._hold.on_update(self.on_hold)

    def note2key(self, note):
        return self._note2key[note[:-1]]

    def play_key(self, note, duration=400):
        key = self.note2key(note)
        self.leds_off()
        self.tune_play(note, duration)
        self.led_on(key)

    def _led_set(self, led_nb, state):
        if isinstance(led_nb, str):
            led_nb = self._key2pos[led_nb]
        self._publish("set/%d" % led_nb, state)

    def led_on(self, led_nb):
        self._led_set(led_nb, "ON")

    def led_off(self, led_nb):
        self._led_set(led_nb, "OFF")

    def leds_on(self):
        self._publish("on", "ON")

    def leds_off(self):
        self._publish("off", "OFF")

    def on_pressed(self, source, value):
        pass

    def on_released(self, source, value):
        pass

    def on_hold(self, source, value):
        pass

