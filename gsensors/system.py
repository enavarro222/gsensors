#-*- coding:utf-8 -*-
import logging
from datetime import datetime

from gsensors import AutoUpdateValue

class CpuUsage(AutoUpdateValue):
    unit = "%"
    update_freq = 1.9

    def update(self):
        import psutil
        self.value = psutil.cpu_percent(interval=0)

