# Copyright (c) 2017, David Sergeant
# Copyrights licensed under the New BSD License
# See the accompanying LICENSE.txt file for terms.
#
# Heavy influence from python-dlipower by
# Copyright (c) 2009-2015, Dwight Hubbard


from __future__ import print_function
from bs4 import BeautifulSoup
import logging
import multiprocessing
import os
import json
import requests
import time
from six.moves.urllib.parse import quote


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
    """indirect caller for instance methods and multiprocessing"""
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
    """ Powerswitch class to manage the Digital Loggers Web power switch """
    __len = 0

    def __init__(self, userid=None, password=None, hostname=None, timeout=None,
                 cycletime=None, retries=None):
        """
        Class initializaton
        """
        if not retries:
            retries = RETRIES
        config = self.load_configuration()
        if retries:
            self.retries = retries
        if userid:
            self.userid = userid
        else:
            self.userid = config['userid']
        if password:
            self.password = password
        else:
            self.password = config['password']
        if hostname:
            self.hostname = hostname
        else:
            self.hostname = config['hostname']
        if timeout:
            self.timeout = float(timeout)
        else:
            self.timeout = config['timeout']
        if cycletime:
            self.cycletime = float(cycletime)
        else:
            self.cycletime = config['cycletime']
        self._is_admin = True

    def __len__(self):
        """
        :return: Number of stations on the switch
        """
        if self.__len == 0:
            self.__len = len(self.statuslist())
        return self.__len

    def __repr__(self):
        """
        display the representation
        """
        if not self.statuslist():
            return "Digital Loggers Web Powerswitch " \
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
            return "Digital Loggers Web Powerswitch " \
                   "%s (UNCONNECTED)" % self.hostname
        output = '<table>' \
                 '<tr><th colspan="3">DLI Web Powerswitch at %s</th></tr>' \
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

    def load_configuration(self):
        """ Return a configuration dictionary """
        if os.path.isfile(CONFIG_FILE):
            file_h = open(CONFIG_FILE, 'r')
            try:
                config = json.load(file_h)
            except ValueError:
                # Failed
                return CONFIG_DEFAULTS
            file_h.close()
            return config
        return CONFIG_DEFAULTS

    def save_configuration(self):
        """ Update the configuration file with the object's settings """
        # Get the configuration from the config file or set to the defaults
        config = self.load_configuration()

        # Overwrite the objects configuration over the existing config values
        config['userid'] = self.userid
        config['password'] = self.password
        config['hostname'] = self.hostname
        config['timeout'] = self.timeout

        # Write it to disk
        file_h = open(CONFIG_FILE, 'w')
        # Make sure the file perms are correct before we write data
        # that can include the password into it.
        os.fchmod(file_h.fileno(), 0o0600)
        if file_h:
            json.dump(config, file_h, sort_keys=True, indent=4)
            file_h.close()
        else:
            raise OpSprException(
                'Unable to open configuration file for write'
            )

    def verify(self):
        """ Verify we can reach the switch, returns true if ok """
        if self.geturl():
            return True
        return False

    def geturl(self, url='index.htm'):
        """ Get a URL from the userid/password protected powerswitch page
            Return None on failure
        """
        full_url = "http://%s/%s" % (self.hostname, url)
        result = None
        request = None
        for i in range(0, self.retries):
            try:
                request = requests.get(full_url, auth=(self.userid, self.password,),  timeout=self.timeout)
            except requests.exceptions.RequestException as e:
                logger.warning("Request timed out - %d retries left.", self.retries - i - 1)
                logger.debug("Catched exception %s", str(e))
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


    def get_station_name(self, station=0):
        """ Return the name of the station """
        station = self.determine_station(station)
        stations = self.statuslist()
        if stations and station:
            for plug in stations:
                if int(plug[0]) == station:
                    return plug[1]
        return 'Unknown'

    def set_station_name(self, station=0, name="Unknown"):
        """ Set the name of an station """
        self.determine_station(station)
        self.geturl(
            url='unitnames.cgi?outname%s=%s' % (station, quote(name))
        )
        return self.get_station_name(station) == name

    def off(self, station=0):
        """ Turn off a power to an station
            False = Success
            True = Fail
        """
        self.geturl(url='station?%d=OFF' % self.determine_station(station))
        return self.status(station) != 'OFF'

    def on(self, station=0):
        """ Turn on power to an station
            False = Success
            True = Fail
        """
        self.geturl(url='station?%d=ON' % self.determine_station(station))
        return self.status(station) != 'ON'

    def cycle(self, station=0):
        """ Cycle power to an station
            False = Power off Success
            True = Power off Fail
            Note, does not return any status info about the power on part of
            the operation by design
        """
        if self.off(station):
            return True
        time.sleep(self.cycletime)
        self.on(station)
        return False

    def statuslist(self):
        """ Return the status of all stations in a list,
        each item will contain 3 items plugnumber, hostname and state  """
        stations = []
        url = self.geturl('index.htm')
        if not url:
            return None
        soup = BeautifulSoup(url, "html.parser")
        # Get the root of the table containing the port status info
        try:
            root = soup.findAll('td', text='1')[0].parent.parent.parent
        except IndexError:
            # Finding the root of the table with the station info failed
            # try again assuming we're seeing the table for a user
            # account insteaed of the admin account (tables are different)
            try:
                self._is_admin = False
                root = soup.findAll('th', text='#')[0].parent.parent.parent
            except IndexError:
                return None
        for temp in root.findAll('tr'):
            columns = temp.findAll('td')
            if len(columns) == 5:
                plugnumber = columns[0].string
                hostname = columns[1].string
                state = columns[2].find('font').string.upper()
                stations.append([int(plugnumber), hostname, state])
        if self.__len == 0:
            self.__len = len(stations)
        return stations

    def printstatus(self):
        """ Print the status off all the stations as a table to stdout """
        if not self.statuslist():
            print(
                "Unable to communicate to the Web power "
                "switch at %s" % self.hostname
            )
            return None
        print('Station\t%-15.15s\tState' % 'Name')
        for item in self.statuslist():
            print('%d\t%-15.15s\t%s' % (item[0], item[1], item[2]))
        return

    def status(self, station=1):
        """
        Return the status of an station, returned value will be one of:
        ON, OFF, Unknown
        """
        station = self.determine_station(station)
        stations = self.statuslist()
        if stations and station:
            for plug in stations:
                if plug[0] == station:
                    return plug[2]
        return 'Unknown'

    def command_on_stations(self, command, stations):
        """
        If a single station is passed, handle it as a single station and
        pass back the return code.  Otherwise run the operation on multiple
        stations in parallel the return code will be failure if any operation
        fails.  Operations that return a string will return a list of strings.
        """
        if len(stations) == 1:
            result = getattr(self, command)(stations[0])
            if isinstance(result, bool):
                return result
            else:
                return [result]
        pool = multiprocessing.Pool(processes=len(stations))
        result = [
            value for value in pool.imap(
                _call_it,
                [(self, command, (station, )) for station in stations],
                chunksize=1
            )
        ]
        if isinstance(result[0], bool):
            for value in result:
                if value:
                    return True
            return result[0]
        return result


if __name__ == "__main__":
    OpenSprinkler().printstatus()
