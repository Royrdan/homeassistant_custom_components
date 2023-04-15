import logging
import voluptuous as vol
from datetime import timedelta
from .foscam.foscam_api import FoscamCamera
import voluptuous as vol
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers import config_validation as cv
from homeassistant.components.switch import (
	ENTITY_ID_FORMAT,
	PLATFORM_SCHEMA,
	SwitchEntity,
)
from homeassistant.const import (
	CONF_HOST,
	CONF_NAME,
	CONF_PASSWORD,
	CONF_PORT,
	CONF_USERNAME,
	CONF_TIMEOUT
)
from .const import (
	DOMAIN,
	LOGGER
	)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
	{
		vol.Required("ip"): cv.string,
		vol.Required(CONF_PASSWORD): cv.string,
		vol.Required(CONF_USERNAME): cv.string,
		vol.Optional(CONF_NAME, default="Foscam Camera"): cv.string,
		vol.Optional(CONF_PORT, default=443): cv.port,
		vol.Optional(CONF_TIMEOUT, default=30): cv.positive_int,
	}
)

SCAN_INTERVAL = timedelta(seconds = 5*30)


async def async_setup_entry(hass, config_entry, async_add_entities):

	# Create Foscam API Class
	camera = FoscamCamera(
		config_entry.data[CONF_HOST],
		config_entry.data[CONF_PORT],
		config_entry.data[CONF_USERNAME],
		config_entry.data[CONF_PASSWORD],
		verbose=False,
		ssl=True,
	)
	# Add switch
	switches = []
	name = config_entry.title
	# Motion Detection
	switches.append(FoscamMotionDetectionSwitch( camera, config_entry ))
	switches.append(FoscamNightVisionSwitch( camera, config_entry ))
	switches.append(FoscamAutoNightVisionSwitch( camera, config_entry ))
	switches.append(FoscamSleepSwitch( camera, config_entry ))

	async_add_entities(switches)


def error_message(self, error_code):
    if error_code == -1:
        LOGGER.error("Couldnt update camera state for " + self._name + ". Format Error", )
    elif error_code == -2:
        LOGGER.error("Couldnt update camera state for " + self._name + ". Auth Error")
    elif error_code == -3:
        LOGGER.error("Couldnt update camera state for " + self._name + ". Command Error")
    elif error_code == -4:
        LOGGER.error("Couldnt update camera state for " + self._name + ". Exectution Error")
    elif error_code == -5:
        LOGGER.error("Couldnt update camera state for " + self._name + ". Timeout")
    elif error_code == -7:
        LOGGER.error("Couldnt update camera state for " + self._name + ". Unknown Error")
    elif error_code == -8:
        LOGGER.error("Couldnt update camera state for " + self._name + ". Unavailable Error")
    else:
        LOGGER.error("Couldnt update camera state for " + self._name + ". Unknown Error")

# Motion Detection
class FoscamMotionDetectionSwitch(SwitchEntity, RestoreEntity):

	def __init__(self, camera, config_entry, timeout=None):
		"""Initialize the switch."""
		self._name = str(config_entry.title + " Cam Motion Detection").title()
		self._friendly_name = self._name.replace('_', ' ').title()
		self._foscam_session = camera
		self._timeout = 30 #config_entry.data[CONF_TIMEOUT]  ###############################3 STILL NEED TO FIX THIS
		self._state = None
		self._icon = 'mdi:motion-sensor'

	async def async_added_to_hass(self):
		"""Register callbacks."""
		# restore state after startup
		await super().async_added_to_hass()
		state = await self.async_get_last_state()
		if state:
			self._state = state.state == "on"

		await super().async_added_to_hass()

	@property
	def is_on(self):
		return self._state

	@property
	def should_poll(self):
		return True

	@property
	def name(self):
		return self._name

	@property
	def friendly_name(self):
		return self._friendly_name

	@property
	def icon(self):
		return self._icon

	def update(self):
		"""Update device state."""
		try:
			ret, current_config = self._foscam_session.get_motion_detect_config(timeout = self._timeout)
			#LOGGER.error("Motion detection status for " + self._name + ": " + str(current_config))
			if ret != 0:
				error_message(self, ret)
			else:
				if current_config['isEnable'] == '1':
					self._state = True
				elif current_config['isEnable'] == '0':
					self._state = False
		except:
			LOGGER.error("Failed to retreive motion detection on " + self._name)
	def turn_on(self):
		"""Enable motion detection in camera."""
		if self._state in [False, None]:
			try:
				ret = self._foscam_session.enable_motion_detection(self._timeout)
				if ret != 0:
					error_message(self, ret)
				else:
					self._state = True
			except:
				LOGGER.error("Failed to enable motion detection on " + self._name)

	def turn_off(self):
		"""Disable motion detection."""
		if self._state in [True, None]:
			try:
				ret = self._foscam_session.disable_motion_detection(self._timeout)
				if ret != 0:
					error_message(self, ret)
				else:
					self._state = False
			except:
				LOGGER.error("Failed to disable motion detection on " + self._name)

# Night Vision
class FoscamNightVisionSwitch(SwitchEntity, RestoreEntity):

	def __init__(self, camera, config_entry, timeout=None):
		"""Initialize the switch."""
		self._name = str(config_entry.title + " Cam Night Vision").title()
		self._friendly_name = self._name.replace('_', ' ').title()
		self._foscam_session = camera
		self._timeout = 30 #config_entry.data[CONF_TIMEOUT]  ############################### STILL NEED TO FIX THIS
		self._state = None
		self._icon = 'mdi:weather-night'

	async def async_added_to_hass(self):
		"""Register callbacks."""
		# restore state after startup
		await super().async_added_to_hass()
		state = await self.async_get_last_state()
		if state:
			self._state = state.state == "on"

		await super().async_added_to_hass()

	@property
	def is_on(self):
		return self._state

	@property
	def should_poll(self):
		return True

	@property
	def name(self):
		return self._name

	@property
	def friendly_name(self):
		return self._friendly_name

	@property
	def icon(self):
		return self._icon

	def update(self):
		"""Update device state."""
		pass # Cannot seem to get the current status of LED. Needs to be assumed
	def turn_on(self):
		"""Enable night vision in camera."""
		if self._state in [False, None]:
			try:
				ret, current_config = self._foscam_session.open_infra_led(timeout = self._timeout)
				if ret != 0:
					error_message(self, ret)
				else:
					self._state = True
			except:
				LOGGER.error("Failed to enable night vision on " + self._name)

	def turn_off(self):
		"""Disable night vision."""
		if self._state in [True, None]:
			try:
				ret, current_config = self._foscam_session.close_infra_led(timeout = self._timeout)
				if ret != 0:
					error_message(self, ret)
				else:
					self._state = False
			except:
				LOGGER.error("Failed to disable night vision on " + self._name)

# Auto Night Vision
class FoscamAutoNightVisionSwitch(SwitchEntity, RestoreEntity):

	def __init__(self, camera, config_entry, timeout=None):
		"""Initialize the switch."""
		self._name = str(config_entry.title + " Cam Auto Night Vision").title()
		self._friendly_name = self._name.replace('_', ' ').title()
		self._foscam_session = camera
		self._timeout = 30 #config_entry.data[CONF_TIMEOUT]  ############################### STILL NEED TO FIX THIS
		self._state = None
		self._icon = 'mdi:theme-light-dark'

	async def async_added_to_hass(self):
		"""Register callbacks."""
		# restore state after startup
		await super().async_added_to_hass()
		state = await self.async_get_last_state()
		if state:
			self._state = state.state == "on"

		await super().async_added_to_hass()

	@property
	def is_on(self):
		return self._state

	@property
	def should_poll(self):
		return True

	@property
	def name(self):
		return self._name

	@property
	def friendly_name(self):
		return self._friendly_name

	@property
	def icon(self):
		return self._icon

	def update(self):
		"""Update device state."""
		try:
			ret, current_config = self._foscam_session.get_infra_led_config(timeout = self._timeout)
			#LOGGER.error("Night Vision status for " + self._name + ": " + str(current_config))

			if ret != 0:
				error_message(self, ret)
			else:
				if current_config['mode'] == '0':
					self._state = True
				elif current_config['mode'] == '1':
					self._state = False
		except:
			LOGGER.error("Failed to retreive night vision status on " + self._name)

	def turn_on(self):
		"""Enable night vision in camera."""
		if self._state in [False, None]:
			try:
				ret, current_config = self._foscam_session.set_infra_led_config(mode=0, timeout = self._timeout)
				if ret != 0:
					error_message(self, ret)
				else:
					self._state = True
			except:
				LOGGER.error("Failed to enable night vision on " + self._name)

	def turn_off(self):
		"""Disable night vision."""
		if self._state in [True, None]:
			try:
				ret, current_config = self._foscam_session.set_infra_led_config(mode =1, timeout = self._timeout)
				if ret != 0:
					error_message(self, ret)
				else:
					self._state = False
			except:
				LOGGER.error("Failed to disable night vision on " + self._name)

# Sleep
class FoscamSleepSwitch(SwitchEntity, RestoreEntity):

	def __init__(self, camera, config_entry, timeout=30):
		"""Initialize the switch."""
		self._name = str(config_entry.title + " Cam Sleep").title()
		self._foscam_session = camera
		if CONF_TIMEOUT in config_entry.data:
			self._timeout = config_entry.data[CONF_TIMEOUT]
		else:
			self._timeout = 30
		self._state = None
		self._icon = 'mdi:sleep'

	async def async_added_to_hass(self):
		"""Register callbacks."""
		# restore state after startup
		await super().async_added_to_hass()
		state = await self.async_get_last_state()
		if state:
			self._state = state.state == "on"

		await super().async_added_to_hass()

	@property
	def is_on(self):
		return self._state

	@property
	def should_poll(self):
		return True

	@property
	def name(self):
		return self._name

	@property
	def friendly_name(self):
		return self._friendly_name

	@property
	def icon(self):
		return self._icon

	def update(self):
		"""Update device state."""
		#pass # Cannot get state needs to be assumed

		try:
			ret, current_config = self._foscam_session.is_asleep(timeout = self._timeout)

			if ret != 0:
				error_message(self, ret)
			else:
				self._state = current_config
		except:
			LOGGER.error("Failed to retreive sleep status status on " + self._name)

	def turn_on(self):
		"""Enable night vision in camera."""
		if self._state in [False, None]:
			try:
				ret, current_config = self._foscam_session.sleep(timeout = self._timeout)
				if ret != 0:
					error_message(self, ret)
				else:
					self._state = True
			except:
				LOGGER.error("Failed to enable sleep on " + self._name)

	def turn_off(self):
		"""Disable night vision."""
		if self._state in [True, None]:
			try:
				ret, current_config = self._foscam_session.wake(timeout = self._timeout)
				if ret != 0:
					error_message(self, ret)
				else:
					self._state = False
			except:
				LOGGER.error("Failed to disable sleep on " + self._name)
