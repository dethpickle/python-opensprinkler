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

    from __future__ import print_function
    from opensprinkler import OpenSprinkler

    print('Connecting to a OpenSprinkler device at demo.opensprinkler.com')
    os = OpenSprinkler(password='a6d82bced638de3def1e9bbb4983225c', hostname='demo.opensprinkler.com')

    print('Turning off the fourth station')
    os.off(3)
    
    print('The state of the fourth station is currently', os.status(3))

    print('Renaming the fourth outlet as "Back Lawn"')
    os.set_station_name(3, 'Back Lawn')

    print('The current status of the powerswitch is:')
    os.statuslist()

    
