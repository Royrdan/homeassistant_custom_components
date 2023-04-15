"""Support for sensor value(s) stored in local files."""
import re
import logging
import os

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import (
    CONF_FILE_PATH,
    CONF_NAME,
)

CONF_IGNORE_LIST = "ignore_list"

import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

reg = "\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{3} ERROR \(.+\) \[.+\] .+"
reg_date = "\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{3} ERROR \(.+?\) "
reg_app = "\[.+\] "

DEFAULT_NAME = "Errors"

ICON = "mdi:alert-circle-outline"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_FILE_PATH): cv.isfile,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_IGNORE_LIST, default = []): cv.ensure_list,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the file sensor."""
    file_path = config.get(CONF_FILE_PATH)
    name = config.get(CONF_NAME)
    ignore_list = config.get(CONF_IGNORE_LIST)

    if hass.config.is_allowed_path(file_path):
        async_add_entities([FileSensor(name, file_path, ignore_list)], True)
    else:
        _LOGGER.error("'%s' is not an allowed directory", file_path)


class FileSensor(SensorEntity):
    """Implementation of a file sensor."""

    def __init__(self, name, file_path, ignore_list):
        """Initialize the file sensor."""
        self._name = name
        self._file_path = file_path
        self._ignore_list = ignore_list
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return ICON

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    def update(self):
        """Get the latest entry from a file and updates the state."""
        try:
            with open(self._file_path, encoding="utf-8") as file_data:
                errors = re.findall(reg, file_data.read())
                if len(errors) == 0:
                    return

                data = re.sub(reg_date, '', errors[-1]) # Remove date at start
                app = re.search(reg_app, data).group() # Get the app name
                app = " ".join(app[1:-2].split(".")[-2:]).title() + ": " # Format the app name and capitalise
                data = re.sub(reg_app, '', data) # Remove the app name
                data = data.replace('{{', '').replace('}}', '').replace('{%','').replace('%}','').replace('\'', '').replace('"', '') # Remove any templating or quotes that may ruin the error post

                cancel = False
                for ignore in self._ignore_list:
                    if ignore.lower() in data.lower():
                        cancel = True
                        break
                if cancel:
                    return

                if len(data) > 255:
                    data = data[0:255]
                data = data.strip()
        except (IndexError, FileNotFoundError, IsADirectoryError, UnboundLocalError):
            _LOGGER.error(
                "File or data not present at the moment: %s",
                os.path.basename(self._file_path),
            )
            return
        if self._state != data:
            self._state = data
