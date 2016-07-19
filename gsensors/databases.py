#-*- coding:utf-8 -*-
import sys
import logging

from influxdb import InfluxDBClient as OriginalInfluxDBClient

class InfluxDBClient(OriginalInfluxDBClient):
    def Publish(self, measurement, tags):
        return InfluxDBPublish(self, measurement, tags)


class InfluxDBPublish(object):

    def __init__(self, influxdb, measurement, tags):
        assert(isinstance(influxdb, OriginalInfluxDBClient))
        self.influxdb = influxdb
        self.tags = tags
        self.measurement = measurement
        self._logger = logging.getLogger("gsensors.InfluxDBPublish")

    def __call__(self, source, value):
        #TODO what when error ?
        json_body = [
            {
                "measurement": self.measurement,
                "tags": self.tags,
                "fields": {
                    "value": value
                }
            }
        ]
        self.influxdb.write_points(json_body)
        self._logger.debug("Write for measurement '%s'" % self.measurement)

