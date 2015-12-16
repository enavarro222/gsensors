#-*- coding:utf-8 -*-
import logging
from datetime import datetime

import gevent
from events import Events

from gsensors.utils import full_exc_info


class Alarm(object):
    """ Alarm system
    """
    def __init__(self, name=None, title=None, msg=None, parent=None):
        self.name = name or self.__class__.__name__
        self._logger = logging.getLogger("gsensors.%s" % self.name)
        self.parent = parent
        self.title = title
        self.msg = msg
        self.id = 0

        self.events = Events()

        self.last_change = None     # datetime on last change
        self.state = 0 # 0: no alarm

    @property
    def active(self):
        return self.state > 0

    #TODO: factorise with DataSource
    def _checked_callback(self, callback):
        def wrapper(*args, **kwargs):
            try:
                callback(*args, **kwargs)
            except Exception as err:
                self.error = "Callback error"
                self._logger.error("Callback error: %s" % err, exc_info=full_exc_info())
        return wrapper

    def on_trigger(self, callback):
        """ Callback when alarm is triggered
        """
        callback = self._checked_callback(callback)
        self.events.on_trigger += callback

    def on_release(self, callback):
        """ Callback when alarm is release
        """
        callback = self._checked_callback(callback)
        self.events.on_release += callback

    def trigger(self, *args, **kwargs):
        """ Trigger the alarm
        """
        if self.parent and self.parent.active:
            return
        if not self.active:
            self.id += 1
            self.last_change = datetime.now()
            self.state = 1
            self._logger.info("Trigger #%d !" % self.id)
            self.events.on_trigger(self)

    def release(self, *args, **kwargs):
        """ Release the alarm
        """
        if self.active:
            self.state = 0
            self.last_change = datetime.now()
            self._logger.info("Release #%d !" % self.id)
            self.events.on_release(self)



