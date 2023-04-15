"""This component provides basic support for Foscam IP cameras."""
from __future__ import annotations
import asyncio
import json

import voluptuous as vol

from homeassistant.components.camera import PLATFORM_SCHEMA, SUPPORT_STREAM, Camera
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.helpers import config_validation as cv, entity_platform

from .const import (
    CONF_RTSP_PORT,
    CONF_STREAM,
    DOMAIN,
    LOGGER,
    SERVICE_PTZ,
    SERVICE_PTZ_PRESET,
    SERVICE_ENABLE_MOTION_DETECTION,
    SERVICE_DISABLE_MOTION_DETECTION,
    SERVICE_ENABLE_NIGHT_VISION,
    SERVICE_DISABLE_NIGHT_VISION,
    SERVICE_SLEEP,
    SERVICE_WAKE,
    SERVICE_CONFIG_MOTION_DETECTION,
    SERVICE_CUSTOM_COMMAND
)
########### ADDED THIS
import sys
#sys.path.append('/mnt/homeassistant/custom_components/foscam')
from .foscam.foscam_api import FoscamCamera
######################

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required("ip"): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Optional(CONF_NAME, default="Foscam Camera"): cv.string,
        vol.Optional(CONF_PORT, default=443): cv.port,
        vol.Optional(CONF_RTSP_PORT): cv.port,
    }
)

DIR_UP = "up"
DIR_DOWN = "down"
DIR_LEFT = "left"
DIR_RIGHT = "right"

DIR_TOPLEFT = "top_left"
DIR_TOPRIGHT = "top_right"
DIR_BOTTOMLEFT = "bottom_left"
DIR_BOTTOMRIGHT = "bottom_right"

MOVEMENT_ATTRS = {
    DIR_UP: "ptz_move_up",
    DIR_DOWN: "ptz_move_down",
    DIR_LEFT: "ptz_move_left",
    DIR_RIGHT: "ptz_move_right",
    DIR_TOPLEFT: "ptz_move_top_left",
    DIR_TOPRIGHT: "ptz_move_top_right",
    DIR_BOTTOMLEFT: "ptz_move_bottom_left",
    DIR_BOTTOMRIGHT: "ptz_move_bottom_right",
}

DEFAULT_TRAVELTIME = 0.125

ATTR_MOVEMENT = "movement"
ATTR_TRAVELTIME = "travel_time"
ATTR_PRESET_NAME = "preset_name"
ATTR_LINKAGE = "linkage"
ATTR_SENSITIVITY = "sensitivity"
ATTR_SNAP_INTERVAL = "snap_interval"
ATTR_TRIGGER_INTERVAL = "trigger_interval"
ATTR_TIMEOUT = "timeout"
ATTR_CUSTOM_COMMAND = "custom_command"
ATTR_PARAMS = "params_string"

PTZ_GOTO_PRESET_COMMAND = "ptz_goto_preset"


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up a Foscam IP Camera."""
    LOGGER.warning(
        "Loading foscam via platform config is deprecated, it will be automatically imported. Please remove it afterwards."
    )

    config_new = {
        CONF_NAME: config[CONF_NAME],
        CONF_HOST: config["ip"],
        CONF_PORT: config[CONF_PORT],
        CONF_USERNAME: config[CONF_USERNAME],
        CONF_PASSWORD: config[CONF_PASSWORD],
        CONF_STREAM: "Main",
        CONF_RTSP_PORT: config.get(CONF_RTSP_PORT, 554),
    }

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=config_new
        )
    )


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add a Foscam IP camera from a config entry."""
    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(
        SERVICE_PTZ,
        {
            vol.Required(ATTR_MOVEMENT): vol.In(
                [
                    DIR_UP,
                    DIR_DOWN,
                    DIR_LEFT,
                    DIR_RIGHT,
                    DIR_TOPLEFT,
                    DIR_TOPRIGHT,
                    DIR_BOTTOMLEFT,
                    DIR_BOTTOMRIGHT,
                ]
            ),
            vol.Optional(ATTR_TRAVELTIME, default=DEFAULT_TRAVELTIME): cv.small_float,
        },
        "async_perform_ptz",
    )

    platform.async_register_entity_service(
        SERVICE_PTZ_PRESET,
        {
            vol.Required(ATTR_PRESET_NAME): cv.string,
        },
        "async_perform_ptz_preset",
    )

    platform.async_register_entity_service(
        SERVICE_ENABLE_MOTION_DETECTION,
        {vol.Optional(ATTR_TIMEOUT): cv.template,},
        "enable_motion_detect",
    )

    platform.async_register_entity_service(
        SERVICE_DISABLE_MOTION_DETECTION,
        {vol.Optional(ATTR_TIMEOUT): cv.template,},
        "disable_motion_detect",
    )

    platform.async_register_entity_service(
        SERVICE_ENABLE_NIGHT_VISION,
        {vol.Optional(ATTR_TIMEOUT): cv.template,},
        "enable_night_vision",
    )

    platform.async_register_entity_service(
        SERVICE_DISABLE_NIGHT_VISION,
        {vol.Optional(ATTR_TIMEOUT): cv.template,},
        "disable_night_vision",
    )

    platform.async_register_entity_service(
        SERVICE_SLEEP,
        {vol.Optional(ATTR_TIMEOUT): cv.template,},
        "sleep",
    )

    platform.async_register_entity_service(
        SERVICE_WAKE,
        {vol.Optional(ATTR_TIMEOUT): cv.template,},
        "wake",
    )

    platform.async_register_entity_service(
        SERVICE_CONFIG_MOTION_DETECTION,
        {
            vol.Required(ATTR_LINKAGE): cv.template,
            vol.Required(ATTR_SENSITIVITY): cv.template,
            vol.Required(ATTR_SNAP_INTERVAL): cv.template,
            vol.Required(ATTR_TRIGGER_INTERVAL): cv.template,
            vol.Optional(ATTR_TIMEOUT): cv.template,
        },
        "configure_motion_detection",
    )

    platform.async_register_entity_service(
        SERVICE_CUSTOM_COMMAND,
        {
        vol.Required(ATTR_CUSTOM_COMMAND): cv.string,
        vol.Optional(ATTR_PARAMS): cv.string,
        vol.Optional(ATTR_TIMEOUT): cv.template,
        },
        "custom_command",
    )

    camera = FoscamCamera(
        config_entry.data[CONF_HOST],
        config_entry.data[CONF_PORT],
        config_entry.data[CONF_USERNAME],
        config_entry.data[CONF_PASSWORD],
        verbose=False,
        ssl=True,
    )

    async_add_entities([HassFoscamCamera(hass, camera, config_entry)])


class HassFoscamCamera(Camera):
    """An implementation of a Foscam IP camera."""

    def __init__(self, hass, camera, config_entry):
        """Initialize a Foscam camera."""
        super().__init__()

        self.hass = hass
        self._foscam_session = camera
        self._name = config_entry.title + "_cam"
        self._username = config_entry.data[CONF_USERNAME]
        self._password = config_entry.data[CONF_PASSWORD]
        self._stream = config_entry.data[CONF_STREAM]
        self._unique_id = config_entry.entry_id
        self._rtsp_port = config_entry.data[CONF_RTSP_PORT]
        self._motion_status = False

    async def async_added_to_hass(self):
        """Handle entity addition to hass."""
        # Get motion detection status
        ret, response = await self.hass.async_add_executor_job(
            self._foscam_session.get_motion_detect_config
        )
        if ret == -3:
            LOGGER.info("Can't get motion detection status, camera %s configured with non-admin user", self._name,)
        elif ret != 0:
            LOGGER.error("Error getting motion detection status of %s: %s", self._name, ret)
        else:
            self._motion_status = response == 1

    def error_message(self, error_code):
        if error_code == -1:
            LOGGER.error("Couldnt configure motion detection for " + self._name + ". Format Error")
        elif error_code == -2:
            LOGGER.error("Couldnt configure motion detection for " + self._name + ". Auth Error")
        elif error_code == -3:
            LOGGER.error("Couldnt configure motion detection for " + self._name + ". Command Error")
        elif error_code == -4:
            LOGGER.error("Couldnt configure motion detection for " + self._name + ". Exectution Error")
        elif error_code == -5:
            LOGGER.error("Couldnt configure motion detection for " + self._name + ". Timeout")
        elif error_code == -7:
            LOGGER.error("Couldnt configure motion detection for " + self._name + ". Unknown Error")
        elif error_code == -8:
            LOGGER.error("Couldnt configure motion detection for " + self._name + ". Unavailable Error")

    @property
    def unique_id(self):
        """Return the entity unique ID."""
        return self._unique_id

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image response from the camera."""
        # Send the request to snap a picture and return raw jpg data
        # Handle exception if host is not reachable or url failed
        result, response = self._foscam_session.snap_picture_2()
        if result != 0:
            return None

        return response

    @property
    def supported_features(self):
        """Return supported features."""
        if self._rtsp_port:
            return SUPPORT_STREAM

        return None

    async def stream_source(self):
        """Return the stream source."""
        self.hass.bus.fire("foscam_stream_started", {"camera": self._name})
        if self._rtsp_port:
            return f"rtsp://{self._username}:{self._password}@{self._foscam_session.host}:{self._rtsp_port}/video{self._stream}"

        return None

    @property
    def motion_detection_enabled(self):
        """Camera Motion Detection Status."""
        return self._motion_status

    def enable_motion_detect(self, timeout=None):
        """Enable motion detection in camera."""
        if timeout == None:
            timeout_int = 10
        else:
            timeout.hass = self.hass
            timeout_int = round( int( float( timeout.async_render(parse_result=False) ) ), 0)
        try:
            ret = self._foscam_session.enable_motion_detection(timeout_int)
            if ret != 0:
                self.error_message(ret)
                return
        except:
            LOGGER.error("Failed enabling motion detection on '%s'.", self._name,)

    def disable_motion_detect(self, timeout=None):
        """Disable motion detection."""
        if timeout == None:
            timeout_int = 10
        else:
            timeout.hass = self.hass
            timeout_int = round( int( float( timeout.async_render(parse_result=False) ) ), 0)
        try:
            ret = self._foscam_session.disable_motion_detection(timeout_int)

            if ret != 0:
                self.error_message(ret)
                return

        except:
            LOGGER.debug("Failed to disable motion detection", self._name,)

    def configure_motion_detection(self, linkage, sensitivity, snap_interval, trigger_interval, timeout=None):
        """Configure motion detection in camera."""
        if timeout == None:
            timeout_int = 10
        else:
            timeout.hass = self.hass
            timeout_int = round( int( float( timeout.async_render(parse_result=False) ) ), 0)
        # Set hass instance of all variables to self.hass so it renders correctly
        linkage.hass = self.hass
        sensitivity.hass = self.hass
        snap_interval.hass = self.hass
        trigger_interval.hass = self.hass

        # Render all templates and ensure no trailing zeros
        linkage_str = str( round(int( float( linkage.async_render(parse_result=False) ) ), 0) )
        sensitivity_str = str( round(int( float( sensitivity.async_render(parse_result=False) ) ), 0) )
        snap_interval_str = str( round( int( float( snap_interval.async_render(parse_result=False) ) ) , 0) )
        trigger_interval_str = str( round(int( float( trigger_interval.async_render(parse_result=False) ) ) - 5, 0) )  # Needs to minus 5 for it to work properly for some reason


        params = {
            "linkage": linkage_str,
            "sensitivity": sensitivity_str,
            "snapInterval": snap_interval_str,
            "triggerInterval": trigger_interval_str,
            "schedule0": 281474976710655, "schedule1": 281474976710655, "schedule2": 281474976710655, "schedule3": 281474976710655, "schedule4": 281474976710655, "schedule5": 281474976710655, "schedule6": 281474976710655, "area0": 1023, "area1": 1023, "area2": 1023, "area3": 1023, "area4": 1023, "area5": 1023, "area6": 1023, "area7": 1023, "area8": 1023, "area9": 1023
        }

        try:
            ret = self._foscam_session.configure_motion_detection(params, timeout=timeout_int)
            if ret != 0:
                self.error_message(ret)
                return

        except TypeError:
            LOGGER.debug("Failed configuring motion detection on '%s'. Is it supported by the device?", self._name,)

    def custom_command(self, custom_command, params_string=None, timeout=None):
        """Send Custom Command to camera"""
        if timeout == None:
            timeout_int = 10
        else:
            timeout.hass = self.hass
            timeout_int = round( int( float( timeout.async_render(parse_result=False) ) ), 0)
        try:
            if params_string:
                params = json.loads(params_string)
        except:
            LOGGER.error(params_string + " is not a valid JSON string for custom command", self._name,)

        try:
            ret = self._foscam_session.execute_command(custom_command, params, timeout=timeout_int)
            if ret != 0:
                self.error_message(ret)
                return
        except:
            LOGGER.error("Failed to send custom command on '%s'.", self._name,)

    def wake(self, timeout=None):
        """Wake Up camera"""
        if timeout == None:
            timeout_int = 10
        else:
            timeout.hass = self.hass
            timeout_int = round( int( float( timeout.async_render(parse_result=False) ) ), 0)
        try:
            ret = self._foscam_session.wake(timeout = timeout_int)

            if ret != 0:
                self.error_message(ret)
                return
        except:
            LOGGER.error("Failed waking camera on '%s'.", self._name,)

    def sleep(self, timeout=None):
        """Put Camera to sleep"""
        if timeout == None:
            timeout_int = 10
        else:
            timeout.hass = self.hass
            timeout_int = round( int( float( timeout.async_render(parse_result=False) ) ), 0)
        try:
            ret = self._foscam_session.sleep(timeout = timeout_int)

            if ret != 0:
                self.error_message(ret)
                return

        except:
            LOGGER.error("Failed to put camera to sleep", self._name,)

    def enable_night_vision(self, timeout=None):
        """Enable night vision"""
        if timeout == None:
            timeout_int = 10
        else:
            timeout.hass = self.hass
            timeout_int = round( int( float( timeout.async_render(parse_result=False) ) ), 0)
        try:
            ret = self._foscam_session.open_infra_led(timeout_int)

            if ret != 0:
                self.error_message(ret)
                return
        except:
            return

    def disable_night_vision(self, timeout=None):
        """Enable night vision"""
        if timeout == None:
            timeout_int = 10
        else:
            timeout.hass = self.hass
            timeout_int = round( int( float( timeout.async_render(parse_result=False) ) ), 0)
        try:
            ret = self._foscam_session.close_infra_led(timeout_int)

            if ret != 0:
                self.error_message(ret)
                return
        except:
            LOGGER.error("Failed to disable night vision", self._name,)

    async def async_perform_ptz(self, movement, travel_time):
        """Perform a PTZ action on the camera."""
        LOGGER.debug("PTZ action '%s' on %s", movement, self._name)

        movement_function = getattr(self._foscam_session, MOVEMENT_ATTRS[movement])

        ret, _ = await self.hass.async_add_executor_job(movement_function)

        if ret != 0:
            LOGGER.error("Error moving %s '%s': %s", movement, self._name, ret)
            return

        await asyncio.sleep(travel_time)

        ret, _ = await self.hass.async_add_executor_job(
            self._foscam_session.ptz_stop_run
        )

        if ret != 0:
            LOGGER.error("Error stopping movement on '%s': %s", self._name, ret)
            return

    async def async_perform_ptz_preset(self, preset_name):
        """Perform a PTZ preset action on the camera."""
        LOGGER.debug("PTZ preset '%s' on %s", preset_name, self._name)

        preset_function = getattr(self._foscam_session, PTZ_GOTO_PRESET_COMMAND)

        ret, _ = await self.hass.async_add_executor_job(preset_function, preset_name)

        if ret != 0:
            LOGGER.error("Error moving to preset %s on '%s': %s", preset_name, self._name, ret)
            return

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name
