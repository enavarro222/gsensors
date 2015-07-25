#-*- coding:utf-8 -*-
import logging
from datetime import datetime
from collections import defaultdict

import gevent


class GSensorApp():
    debug = False

    def __init__(self):
        self.sources = []

    def add(self, source):
        self.sources.append(source)
        source.debug = self.debug

    def run(self):
        for source in self.sources:
            source.start()
        # wait
        gevent.wait()


class DataSource(object):
    """ Abstract data source model
    """
    debug = False
    timeout = -1 # no timeout by default

    def __init__(self, name=None, unit=None, timeout=None):
        self.name = name or self.__class__.__name__
        self._logger = logging.getLogger("gsensors.%s" % self.name)

        self.unit = unit
        self._value = 0
        self._error = None

        if timeout is not None:
            self.timeout = timeout
        self.cb_changed = []
        self.cb_value = defaultdict(list)
        self.last_update = None     # datetime on last update

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        """ Reset the value (and last_update) if the value changed OR if the
        timeout is over.
        
        To force update with same value (within timeout)
        """
        now = datetime.now()
        if val != self._value or (timeout >= 0 and now-self.last_update > timeout):
            self._value = val
            self.last_update = now
            self._changed()

    def set_value(self, val, update_time=None):
        """ Set the value (and update_time)
        
        Callbacks are trigger if update_time or value haved changed
        """
        changed = self._value != val or self.last_update != update_time
        self._value = val
        if update_time is None:
            update_time = datetime.now()
        self.last_update = update_time
        if changed:
            self._changed()

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, err):
        if err != self._error:
            self._error = err
            self._changed()

    def _changed(self):
        self.last_update = datetime.now()
        for callback in self.cb_value[self.value]:
            callback(self)
        for callback in self.cb_changed:
            callback(self)

    def on_change(self, callback):
        self.cb_changed.append(callback)

    def on_value(self, value, callback):
        self.cb_value[value].append(callback)

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
        """
        self.value = 0
        self.error = None
        raise NotImplementedError("Should be overiden in subclass")

    def checked_update(self):
        try:
            self.update()
        except Exception as err:
            self.error = "Error"
            self._logger.error("update error: %s" % err)
            if self.debug:
                raise

    def update_work(self):
        while True:
            self._logger.info("Update !")
            self.checked_update()
            gevent.sleep(self.update_freq)

    def start(self):
        self.worker = gevent.spawn(self.update_work)



class StupidCount(AutoUpdateValue):
    unit = ""
    update_freq = 1

    def update(self):
        self.value += 1

