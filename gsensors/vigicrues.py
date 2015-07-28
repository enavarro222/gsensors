#-*- coding:utf-8 -*-
import sys
from time import time
from datetime import datetime

from gsensors import AutoUpdateValue

class VigicruesStation(object):
    """ Simple class to scrap data from vigicrues website (http://www.vigicrues.gouv.fr/)
    """
    #TODO: récupérer les info sur la station (vile/nom/rivière)
    #TODO: récupérer les débit si disonible

    ttl = 15*60 # make a request every 15mins max

    def __init__(self, station_id):
        self.station_id = station_id
        self._data = None
        self._last_update = 0
        self.nb_heures = 1 # by default fetch the data just for the last hour

    @property
    def url_hauteur(self):
        return "http://www.vigicrues.gouv.fr/niveau3.php?idstation=%s&idspc=25&typegraphe=h&AffProfondeur=%d&AffRef=auto&AffPrevi=non&&ong=2" % (self.station_id, self.nb_heures)

    @property
    def data(self):
        _last_update = time()
        if self._data is None or abs(_last_update - self._last_update) > self.ttl:
            self._data = self._get_data()
            self._last_update = _last_update
        return self._data

    def _get_data(self):
        from pyquery import PyQuery as pq
        data = pq(url=self.url_hauteur)
        # get table datas
        all_values = ([td.text for td in pq(tr)("td")] for tr in data("table.liste tr"))
        # filter header
        all_values = (line for line in all_values if len(line))
        # data conversion
        all_values = ((datetime.strptime(date, '%d/%m/%Y %H:%M'), float(hauteur)) for date, hauteur in all_values)
        return list(all_values)

    @property
    def date(self):
        return self.data[0][0]

    @property
    def hauteur(self):
        return  self.data[0][1]


class VigicruesSource(AutoUpdateValue):
    def __init__(self, station_id, name=None):
        """
        :attr station_id: vigicrues station id
        """
        if name is None:
            name = "vgs%d" % station_id
        #:attr vgs: :class:`VigicruesStation` instance
        #self.vgs = vgs
        #assert isinstance(vgs, VigicruesStation)
        self.vgs = VigicruesStation(station_id)
        update_freq = self.vgs.ttl
        super(VigicruesSource, self).__init__(name=name, unit="m", update_freq=update_freq)

    def update(self):
        self.set_value(self.vgs.hauteur, self.vgs.date)


def main():
    vgs = VigicruesStation(297)
    print("Station #%s" % (vgs.station_id))
    print("## Hauteur %1.2fm le %s" % (vgs.hauteur, vgs.date))
    print("## nb feetched data : %s" % (len(vgs.data)))

if __name__ == '__main__':
    sys.exit(main())


