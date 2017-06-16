# Copyright (c) 2017, David Sergeant
# Copyrights licensed under the New BSD License
# See the accompanying LICENSE.txt file for terms.
#
# Heavy influence from python-dlipower by
# Copyright (c) 2009-2015, Dwight Hubbard


from __future__ import print_function
from bs4 import BeautifulSoup
import logging
import os
import json
import requests
import time
from six.moves.urllib.parse import quote
from urllib import urlencode


logger = logging.getLogger(__name__)


# Global settings
TIMEOUT = 20
RETRIES = 3
CYCLETIME = 3
CONFIG_DEFAULTS = {
    'timeout': TIMEOUT,
    'cycletime': CYCLETIME,
    'userid': 'admin',
    'password': '4321',
    'hostname': '192.168.0.100'
}
CONFIG_FILE = os.path.expanduser('~/.dlipower.conf')


def _call_it(params):   # pragma: no cover
    """indirect caller for instance methods"""
    instance, name, args = params
    kwargs = {}
    return getattr(instance, name)(*args, **kwargs)


class OpSprException(Exception):
    """
    An error occurred talking to the OpenSprinkler unit
    """
    pass


class Station(object):
    """
    An OpenSprinkler individual station class
    """
    use_description = True

    def __init__(self, switch, station_number, description=None, state=None):
        self.switch = switch
        self.station_number = station_number
        self.description = description
        if not description:
            self.description = str(station_number)
        self._state = state

    def __unicode__(self):
        name = None
        if self.use_description and self.description:  # pragma: no cover
            name = '%s' % self.description
        if not name:
            name = '%d' % self.station_number
        return '%s:%s' % (name, self._state)

    def __str__(self):
        return self.__unicode__()

    def __repr__(self):
        return "<dlipower_station '%s'>" % self.__unicode__()

    def _repr_html_(self):  # pragma: no cover
        """ Display representation as an html table when running in ipython """
        return u"""<table>
    <tr><th>Description</th><th>Station Number</th><th>State</th></tr>
    <tr><td>{0:s}</td><td>{1:s}</td><td>{2:s}</td></tr>
</table>""".format(self.description, self.station_number, self.state)

    @property
    def state(self):
        """ Return the station state """
        return self._state

    @state.setter
    def state(self, value):
        """ Set the station state """
        self._state = value
        if value in ['off', 'OFF', '0']:
            self.off()
        if value in ['on', 'ON', '1']:
            self.on()

    def off(self):
        """ Turn the station off """
        return self.switch.off(self.station_number)

    def on(self):
        """ Turn the station on """
        return self.switch.on(self.station_number)

    def rename(self, new_name):
        """
        Rename the station
        :param new_name: New name for the station
        :return:
        """
        return self.switch.set_station_name(self.station_number, new_name)

    @property
    def name(self):
        """ Return the name or description of the station """
        return self.switch.get_station_name(self.station_number)

    @name.setter
    def name(self, new_name):
        """ Set the name of the station """
        self.rename(new_name)


class OpenSprinkler(object):
    """ Powerswitch class to manage the OpenSprinker device """
    __len = 0

    def __init__(self, password=None, hostname=None, defaultstationruntime=10,
                 fulldatarefresh=300):
        """
        Class initializaton
        """
        self.password = password
        self.hostname = hostname
        self.defaultruntime = defaultruntime
        self.fulldatarefresh = fulldatarefresh
        response = self.getfullstatus()
            if not response:
                raise OpSprException('Could not contact OpenSprinkler host')



    def __len__(self):
        """
        :return: Number of stations on the switch
        """
        if self.__len == 0:
            self.__len = self.__lastfullresponse['status']['nstations']
        return self.__len

    def __repr__(self):
        """
        display the representation
        """
        if not self.statuslist():
            return "OpenSprinkler " \
                   "%s (UNCONNECTED)" % self.hostname
        output = 'OpenSprinkler at %s\n' \
                 'Station\t%-15.15s\tState\n' % (self.hostname, 'Name')
        for item in self.statuslist():
            output += '%d\t%-15.15s\t%s\n' % (item[0], item[1], item[2])
        return output

    def _repr_html_(self):
        """
        __repr__ in an html table format
        """
        if not self.statuslist():
            return "OpenSprinkler " \
                   "%s (UNCONNECTED)" % self.hostname
        output = '<table>' \
                 '<tr><th colspan="3">OpenSprinkler at %s</th></tr>' \
                 '<tr>' \
                 '<th>Station Number</th>' \
                 '<th>Station Name</th>' \
                 '<th>Station State</th></tr>\n' % self.hostname
        for item in self.statuslist():
            output += '<tr><td>%d</td><td>%s</td><td>%s</td></tr>\n' % (
                item[0], item[1], item[2])
        output += '</table>\n'
        return output

    def __getitem__(self, index):
        stations = []
        if isinstance(index, slice):
            status = self.statuslist()[index.start:index.stop]
        else:
            status = [self.statuslist()[index]]
        for station_status in status:
            power_station = Station(
                switch=self,
                station_number=station_status[0],
                description=station_status[1],
                state=station_status[2]
            )
            stations.append(power_station)
        if len(stations) == 1:
            return stations[0]
        return stations

    def getfullstatus(self)
        if (self.__lastfullresponse["settings"]["devt"] +
            self.fulldatarefresh) < time.time():
            response = self.geturl('ja')
            if response.status_code != 200:
                return False
            self.__lastfullresponse = response.json()
        return True

    def verify(self):
        """ Verify we can reach the switch, returns true if ok """
        if self.geturl():
            return True
        return False

    def geturl(self, url='js', commands=None):
        """ Get a URL from the password protected opensprinkler page
            Return None on failure
        """
        full_url = "http://%s/%s?pw=%s" % (self.hostname, url, self.password)
        if not commands:
            full_url = full_url + commands
        result = None
        request = None
        for i in range(0, self.retries):
            try:
                request = requests.get(full_url, auth=(self.userid, self.password,),  timeout=self.timeout)
            except requests.exceptions.RequestException as e:
                logger.warning("Request timed out - %d retries left.", self.retries - i - 1)
                logger.debug("Caught exception %s", str(e))
                continue
            if request.status_code == 200:
                result = request.content
                break
        logger.debug('Response code: %s', request.status_code)
        return result

    def determine_station(self, station=None):
        """ Get the correct station number from the station passed in, this
            allows specifying the station by the name and making sure the
            returned station is an int
        """
        stations = self.statuslist()
        if station and stations and isinstance(station, str):
            for plug in stations:
                plug_name = plug[1]
                if plug_name and plug_name.strip() == station.strip():
                    return int(plug[0])
        try:
            station_int = int(station)
            if station_int <= 0 or station_int > self.__len__():
                raise OpSprException('Station number %d out of range' % station_int)
            return station_int
        except ValueError:
            raise OpSprException('Station name \'%s\' unknown' % station)


    def station_name_list()
        return self.__lastfullresponse["stations"]["snames"]

    def get_station_name(self, station=0):
        """ Return the name of the station """
        return self.statuslist()[station][2]

    def set_station_name(self, station=0, name="Unknown"):
        """ Set the name of an station """
        commandlist = '&s%s=%s' % (station, urlencode(name))
        self.geturl(
            url='cs', commands=commandlist)
        return self.get_station_name(station) == name

    def off(self, station=0):
        """ Turn off a power to an station
            False = Success
            True = Fail
        """
        commandlist = '&sid=%s&en=0&t=%s' % (station, duration)
        self.geturl(url='cm', commands=commandlist)
        return self.status(station) != 'OFF'

    def on(self, station=0, duration=self.defaultruntime):
        """ Turn on power to an station
            False = Success
            True = Fail
        """
        commandlist = '&sid=%s&en=1&t=%s' % (station, duration)
        self.geturl(url='cm', commands=commandlist)
        return self.status(station) != 'ON'

    def statuslist(self):
        """ Return the status of all stations in a list,
        each item will contain 3 items station number, state and
        station name  """
        response = self.geturl('js')
        if not response:
            return None
        data = response.json()
        states = data["status"]["sn"]
        stations = zip(range(0,data["status"]["nstations"]),
            ['ON' if x==1 else 'OFF' for x in states],
            data["stations"]["snames"])
        return stations

    def printstatus(self):
        """ Print the status off all the stations as a table to stdout """
        data = self.statuslist()
        if not data:
            print(
                "Unable to communicate to the OpenSprinkler "
                "at %s" % self.hostname
            )
            return None
        print('Station\t%-15.15s\tState' % 'Name')
        for item in data:
            print('%d\t%-15.15s\t%s' % (item[0], item[1], item[2]))
        return

    def status(self, station=1):
        """
        Return the status of a given station
        """
        return self.statuslist()[station][1]

if __name__ == "__main__":
    OpenSprinkler().printstatus()
