"""Constants for Foscam component."""
import logging

LOGGER = logging.getLogger(__package__)

DOMAIN = "foscam"

CONF_RTSP_PORT = "rtsp_port"
CONF_STREAM = "stream"

SERVICE_PTZ = "ptz"
SERVICE_PTZ_PRESET = "ptz_preset"
SERVICE_ENABLE_MOTION_DETECTION = "enable_motion_detection"
SERVICE_DISABLE_MOTION_DETECTION = "disable_motion_detection"
SERVICE_ENABLE_NIGHT_VISION = "enable_night_vision"
SERVICE_DISABLE_NIGHT_VISION = "disable_night_vision"
SERVICE_SLEEP = "sleep"
SERVICE_WAKE = "wake"
SERVICE_CONFIG_MOTION_DETECTION = "config_motion_detection"
SERVICE_CUSTOM_COMMAND = "custom_command"
