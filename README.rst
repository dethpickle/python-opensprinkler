OpenSprinkler Python Module
**************************************************


DESCRIPTION
===========
This is a python module to control OpenSprinkler hardware
              
The module provides a python class named
OpenSprinkler that allows managing the device
from python programs.


SUPPORTED DEVICES
=================
This module has been tested against the following 
OpenSprinkler versions:

* OpenSprinkler Hardware 3.0
* firmware 2.1.7


Example
=======

.. code-block:: python

        import opensprinkler

        print('Connecting to a OpenSprinkler device at demo.opensprinkler.com')
        # password is md5 hash of the OpenSprinkler password, like the API uses
        # the demo site password is always 'opendoor'
        os = OpenSprinkler(password='a6d82bced638de3def1e9bbb4983225c', hostname='demo.opensprinkler.com')

    Connecting to a OpenSprinkler device at demo.opensprinkler.com

        print(os)

    OpenSprinkler at demo.opensprinkler.com
    Station Name            State
    0   S01             ON
    1   Station 2       OFF
    2   S03             OFF
    3   S04             OFF
    4   S05             OFF
    5   S06             OFF
    6   S07             ON
    7   S08             OFF

        print('Or iterate across it...')
        for item in os:
            print(item.name, item.station_number, item.state)
        
    Or iterate across it...
    S01 0 ON
    Station 2 1 OFF
    S03 2 OFF
    S04 3 OFF
    S05 4 OFF
    S06 5 OFF
    S07 6 ON
    S08 7 ON

        print('Turning off the fourth station')
        os.off(3)
    
    Turning off the fourth station    
    False

        print('The state of the fourth station is currently', os.status(3))

    The state of the fourth station is currently 'OFF'

        print('Renaming the fourth outlet as "Back Lawn"')
        os.set_station_name(3, 'Back Lawn')

    Renaming the fourth outlet as "Back Lawn"
    True

        print('The current status of the device is:')
        os.statuslist()

    The current status of the device is:
    [(0, 'S01', 'OFF'),
     (1, 'Station 2', 'OFF'),
     (2, 'S03', 'OFF'),
     (3, 'Back Lawn', 'OFF'),
     (4, 'S05', 'OFF'),
     (5, 'S06', 'OFF'),
     (6, 'S07', 'OFF'),
     (7, 'S08', 'OFF')]
    
