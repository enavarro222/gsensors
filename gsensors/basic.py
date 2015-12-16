#-*- coding:utf-8 -*-
import logging
from datetime import datetime

import gevent
from events import Events

from gsensors.utils import full_exc_info

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
   #TODO
   
    def __init__(self, name=None, unit=None, timeout=None):
        self.name = name or self.__class__.__name__
        self._logger = logging.getLogger("gsensors.%s" % self.name)

        self.events = Events()

        self.unit = unit
        self._value = 0
        self._error = None

        if timeout is not None:
            self.timeout = timeout
        self.last_update = None     # datetime on last update

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        """ Set/Update the value
        """
        now = datetime.now()
        self.set_value(val, update_time=now)

    def set_value(self, val, update_time=None):
        self.events.on_update(self, val)
        if val != self._value:
            self._value = val
            self.last_update = update_time
            self.events.on_change(self, val)

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, err):
        if err != self._error:
            # call error listener
            old_err = self._error
            self._error = err
            if self._error is not None:
                self.events.on_error(self, err)
            else:
                self.events.on_error_release(self, old_err)

    def _checked_callback(self, callback):
        def wrapper(*args, **kwargs):
            try:
                callback(*args, **kwargs)
            except Exception as err:
                self.error = "Callback error"
                self._logger.error("Callback error: %s" % err, exc_info=full_exc_info())
        return wrapper

    def _callback_wrap_onvalue(self, callback, value):
        if callable(value):
            def wrapper(source, new_value):
                if value(new_value):
                    callback(new_value)
        else:
            def wrapper(source, new_value):
                #self._logger.debug("%s =? %s" % (new_value, value))
                if new_value == value:
                    callback(new_value)
        return wrapper

    def on_update(self, callback, value=None):
        """ Callback when value is updated (even if it stays the same). 
        
        If `value` is given the callback will be called only if the new value
        equals it.
        """
        if value is not None:
            callback = self._callback_wrap_onvalue(callback, value)
        callback = self._checked_callback(callback)
        self.events.on_update += callback

    def on_change(self, callback, value=None):
        """ Callback when value changed. If `value` is given the callback
        will be called only if the new value equals it.
        """
        if value is not None:
            callback = self._callback_wrap_onvalue(callback, value)
        callback = self._checked_callback(callback)
        self.events.on_change += callback

    def on_timeout(self, callback):
        #TODO
        raise NotImplementedError

    def on_error(self, callback):
        """ Callback when an error occurs (property error changed and is not None)
        """
        callback = self._checked_callback(callback)
        self.events.on_error += callback

    def on_error_release(self, callback):
        """ Callback when there is no more error (property error changed back to None)
        """
        callback = self._checked_callback(callback)
        self.events.on_error_release += callback

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

    def _checked_update(self):
        try:
            self.update()
        except Exception as err:
            self.error = "Error"
            self._logger.error("Update error: %s" % err, exc_info=full_exc_info())

    def update_work(self):
        while True:
            self._logger.info("Update !")
            self._checked_update()
            gevent.sleep(self.update_freq)

    def start(self):
        self.worker = gevent.spawn(self.update_work)


class StupidCount(AutoUpdateValue):
    unit = ""
    update_freq = 1

    def update(self):
        self.value += 1


def cb_print(source):
    print("%s: %s%s" % (source.name, source.value, source.unit))


def PrintValue():
    def _print(source, value):
        print("%s: %s %s" % (source.name, value, source.unit if source.unit is not None else ""))
    return _print

def PrintError():
    def _print(source, error):
        print("%s ERROR: %s" % (source.name, error))
    return _print
