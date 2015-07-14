#-*- coding:utf-8 -*-
import logging
from datetime import datetime

import gevent

class DataSource(object):
    """ Abstract data source model
    """
    timeout = 1*60 # by default 1min

    def __init__(self, name=None, unit=None, timeout=None):
        self.name = name or self.__class__.__name__
        self.unit = unit
        self.value = 0
        self.error = None
        if timeout is not None:
            self.timeout = timeout
        self.callbacks = []
        self.last_update = None     # datetime on last update
        self._logger = logging.getLogger("gsensors.%s" % self.name)

    def on_change(self, callback):
        self.callbacks.append(callback)

    def changed(self):
        self.last_update = datetime.now()
        for callback in self.callbacks:
            callback(self)

    def start(self):
        pass

    def export(self):
        """ Data given to the clients on each change
        """
        res = {}
        res["type"] = self.__class__.__name__
        res["name"] = self.name
        res["timeout"] = self.timeout
        res["value"] = self.value
        res["unit"] = self.unit
        res["error"] = self.error
        if self.last_update is not None:
            res["last_update"] = self.last_update.isoformat()
        return res

    def desc(self):
        res = {}
        res["type"] = self.__class__.__name__
        res["name"] = self.name
        return res


class AutoUpdateValue(DataSource):
    """ Basic value source model: 
    * a single value (with a label and a unit)
    * an update methode called every N seconds
    """
    unit = ""
    update_freq = 1     # frequence of update

    def __init__(self, name=None, unit=None, update_freq=None):
        super(AutoUpdateValue, self).__init__(name=name, unit=unit)
        # update timeput
        self.worker = None
        self.last_update = None
        if update_freq is not None:
            self.update_freq = update_freq or AutoUpdateValue.update_freq
        self.timeout = self.update_freq * 2 # timeout after 2 update fail
        # datetime of last and previous read (self.update return datetime)
        self.last_read = None
        self.prevous_read = None

    def update(self):
        """ Abstract update method
        
        Returns None or the last date of the setted value
        """
        return None

    def checked_update(self):
        try:
            self.prevous_read = self.last_read
            # run the update and get last_read "date"
            last_read = self.update()
            # check error
            self.error = None
            if last_read is None:
                last_read = datetime.now()
            self.last_read = last_read
            if self.last_read != self.prevous_read:
                self.changed()
        except Exception as err:
            self.error = "Error"
            self.changed()
            self._logger.error("update error: %s" % err)

    def update_work(self):
        while True:
            self._logger.info("Update !")
            self.checked_update()
            gevent.sleep(self.update_freq)

    def start(self):
        self.checked_update()
        self.worker = gevent.spawn(self.update_work)



class StupidCount(AutoUpdateValue):
    unit = ""
    update_freq = 1

    def update(self):
        self.value += 1

