"""
Support for ACMeda covers.

For more details about this component, please refer to the documentation at
...
"""

import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant.util import Throttle
from datetime import timedelta


from homeassistant.const import (
    CONF_PORT,CONF_COVERS,CONF_FRIENDLY_NAME,EVENT_HOMEASSISTANT_STOP,
    SERVICE_OPEN_COVER, SERVICE_CLOSE_COVER, SERVICE_SET_COVER_POSITION,
    STATE_OPEN,STATE_CLOSED, STATE_UNKNOWN, STATE_OPENING, STATE_CLOSING, ATTR_ENTITY_ID)
    
    
from homeassistant.components.cover import (
    ATTR_POSITION, CoverDevice,
    PLATFORM_SCHEMA, SUPPORT_CLOSE,
    SUPPORT_OPEN, SUPPORT_SET_POSITION
)
from homeassistant.util.async_ import run_coroutine_threadsafe

import homeassistant.helpers.config_validation as cv

"""REQUIREMENTS = ['PulseAPI']"""

_LOGGER = logging.getLogger(__name__)

COVER_FEATURES = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION

CLOSED_POSITION = 0
OPEN_POSITION = 100
CONF_HUB_ID = 'hub_id'
CONF_MOTOR_ID = 'motor_id'
#SCAN_INTERVAL = timedelta(seconds=60)
MIN_TIME_BETWEEN_SCANS = timedelta(seconds=2)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_PORT): cv.string
})

async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the pulse platform."""
    from .PulseApi import PulseApi
    # pylint: disable=no-name-in-module
    port = config[CONF_PORT]
    papi = PulseApi(port)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, papi.stop_serial_read())
    #hass._serial_loop_task = hass.loop.create_task(papi.main(hass))
    #hass._serial_loop_task = hass.loop.create_task(papi.serial_read())
    hass.async_create_task(papi.main(hass))
    devices = config.get(CONF_COVERS, {})
    covers = []

    for device_name, device_config in devices.items():
        covers.append(
            PulseCover(
                papi,
                device_config.get(CONF_FRIENDLY_NAME, device_name),
                device_config.get(CONF_HUB_ID),
                device_config.get(CONF_MOTOR_ID)

            )
        )

    if not covers:
        _LOGGER.error("No covers added")
        return False

    async_add_entities(covers, True)
    
    


class PulseCover(CoverDevice):
    """
    Representation of a Pulse cover device.

    """

    def __init__(self, papi, name, hub_id, motor_id):
        """Init the Pulse device."""
        self._papi = papi
        self._name = name
        self._hub_id = hub_id
        self._motor_id = motor_id
        self._state = None
        self._available = None
        self._current_cover_position = 0

    @property
    def name(self):
        """Return the name of the device as reported by tellcore."""
        return self._name

    @property
    def available(self):
        """Could the device be accessed during the last update call."""
        return self._available

    @property
    def current_cover_position(self):
        """
        Return current position of cover.

        None is unknown, 100 is closed, 0 is fully open.
        """
        try:
            self._current_cover_position = int(self._papi.getMotorPosition(self._hub_id,self._motor_id))
            return self._current_cover_position
        except:
            pass
        return 0
        

    @property
    def request_cover_position(self):
        """
        Return request position of cover.

        The request position is the position of the last request
        to Pulse Hub
        """
        try:
            self._current_cover_position = int(self._papi.getMotorPosition(self._hub_id,self._motor_id))
            return self._current_cover_position
        except:
            pass
        return 0



    @property
    def state(self):
        """Return the state of the cover."""


        closed = self.is_closed

        if closed is None:
            return STATE_UNKNOWN

        return STATE_CLOSED if closed else STATE_OPEN

   
    @property
    def supported_features(self):
        """Flag supported features."""
        return COVER_FEATURES

    @property
    def is_closed(self):
        _LOGGER.debug("checking %s %s is CLOSEd %d " % (self._hub_id, self._motor_id, self.current_cover_position))

        """Return true if cover is closed, else False."""
        return self.current_cover_position == CLOSED_POSITION
    @Throttle(MIN_TIME_BETWEEN_SCANS) 
    def update(self):
        """Poll the current state of the device."""
        try:
            self._state = self._papi.Request_Current_Possition(self._hub_id,self._motor_id)
            self._available = True
        except (TypeError, KeyError, NameError, ValueError) as ex:
            _LOGGER.error("%s", ex)
            self._available = False
    def open_cover(self, **kwargs):
        """Set the cover to the open position."""
        self._papi.set_cover_position(self._hub_id,self._motor_id, OPEN_POSITION)
        

    def close_cover(self, **kwargs):
        """Set the cover to the closed position."""
        self._papi.set_cover_position(self._hub_id,self._motor_id, CLOSED_POSITION)
 
    @Throttle(MIN_TIME_BETWEEN_SCANS) 
    def set_cover_position(self, **kwargs):
        """Set the cover to a specific position."""
        _LOGGER.debug("moving motor %s to %d"%(self._motor_id, kwargs[ATTR_POSITION]))
        self._papi.set_cover_position(self._hub_id,self._motor_id, kwargs[ATTR_POSITION])

