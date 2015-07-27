#-*- coding:utf-8 -*-
import logging

import psutil

from gsensors import AutoUpdateValue

class CpuUsage(AutoUpdateValue):
    unit = "%"
    update_freq = 1.9

    def update(self):
        self.value = psutil.cpu_percent(interval=0)

