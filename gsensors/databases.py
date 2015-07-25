#-*- coding:utf-8 -*-
import sys

from influxdb import InfluxDBClient

class InfluxDBPublish(object):

    def __init__(self, influxdb, measurement, tags)
        assert(isinstance(influxdb, InfluxDBClient))
        self.influxdb = influxdb
        self.tags = tags
        self.measurement = measurement

    def __call__(self, source):
        #TODO what when error ?
        json_body = [
            {
                "measurement": self.measurement,
                "tags": self.tags,
                "fields": {
                    "value": source.value
                }
            }
        ]
        self.influxdb.write_points(json_body)


