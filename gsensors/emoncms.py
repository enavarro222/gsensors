#-*- coding:utf-8 -*-
import logging
import gevent

from gsensors import AutoUpdateValue

class EmoncmsSource(AutoUpdateValue):
    update_freq = 30 # every minutes by default

    def __init__(self, name, emoncms_client, feedid, unit=None, update_freq=None):
        self.emoncms_client = emoncms_client
        self.feedid = feedid
        self.plots_cfg = {}
        self.plots = {}
        super(EmoncmsSource, self).__init__(name=name, unit=unit, update_freq=update_freq)

    def add_plot(self, plot_name, delta_sec, nb_data):
        self.plots_cfg[plot_name] = {
            "delta_sec": delta_sec,
            "nb_data": nb_data,
        }
        self.checked_update()

    def update(self):
        values = self.emoncms_client.get_value(self.feedid)
        self.value = float(values["value"])
        for plot_name, plot_cfg in self.plots_cfg.iteritems():
            # TODO check if update needed
            self.plots[plot_name] = self.emoncms_client.get_data(fid=self.feedid, **plot_cfg)
        return values["date"]

    def export(self):
        res = super(EmoncmsSource, self).export()
        res["plots"] = self.plots.keys()
        for plot_name, plot_data in self.plots.iteritems():
            res[plot_name] = [
                {"date": date, "value": val} for date, val in plot_data.iteritems()
            ]
        return res

