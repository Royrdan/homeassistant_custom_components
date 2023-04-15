"""
Binary Sensor to scrape the calendar dates for which bin needs emptying
"""

import logging # Allows logging
from datetime import date, datetime, timedelta
import requests
from bs4 import BeautifulSoup as bs
import re


import voluptuous as vol # Voluptuous checks all the config entries are valid

from homeassistant.components.sensor import PLATFORM_SCHEMA # Not sure what this does
from homeassistant.const import CONF_NAME, CONF_USERNAME, CONF_PASSWORD # Load all config components from const.py in core
from homeassistant.helpers.entity import Entity # Import binary sensor component
import homeassistant.helpers.config_validation as cv # Import config validation

_LOGGER = logging.getLogger(__name__) # Create logger

# Config items compatible with this module
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)

SCAN_INTERVAL = timedelta(hours=1)

site = "https://mycouncil.sunshinecoast.qld.gov.au/account/login"
login_site = "https://sccmycouncil.b2clogin.com/sccmycouncil.onmicrosoft.com/B2C_1_StandardSignUpIn/SelfAsserted"
confirmed_site = "https://sccmycouncil.b2clogin.com/sccmycouncil.onmicrosoft.com/B2C_1_StandardSignUpIn/api/CombinedSigninAndSignup/confirmed"
base_site = 'https://mycouncil.sunshinecoast.qld.gov.au/'

def setup_platform(hass, config, add_entities, discovery_info=None):
    sensor_name = config.get(CONF_NAME)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    add_entities([bin_day_sensor(sensor_name, username, password)], True)

class bin_day_sensor(Entity):
    """Implementation of a Workday sensor."""

    def __init__(self, name, username, password):
        self._name = name
        self._username = username
        self._password = password
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        if self._state == 'Recycle':
            return 'mdi:recycle'
        else:
            return 'mdi:pine-tree'

    @property
    def extra_state_attributes(self):
        return self._attributes

    def update(self):
        """Update all data and set in self.____"""
        if 'last_updated' in self._attributes:
            if self._attributes['last_updated'] == str(date.today()):
                return

        def check_response(response):
            if response.status_code > 399:
                logger.error("Call failed with response code " + str(response.status_code), self._name)
            else:
                return response

        data = {
        'request_type': 'RESPONSE',
        'logonIdentifier': self._username,
        'password': self._password
        }
        r = requests.session() # Start requests session
        login = check_response(r.get(site)) # Load login page

        try:
            csrf_token = re.findall('"csrf":".*?"', login.text)[0].replace('"', '').replace('csrf:', '') # Pull the CSRF token from script page
        except:
            LOGGER.error("Failed to get CSRF token for bin day sensor. Will attempt again in 6 hours"  ,self._name)
        # Load headers
        headers = {
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-CSRF-TOKEN': csrf_token,
            'X-Requested-With': 'XMLHttpRequest',
            'sec-ch-ua-mobile': '?0',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://sccmycouncil.b2clogin.com',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Accept-Language': 'en-US,en-AU;q=0.9,en;q=0.8',
        }
        check_response(r.post(login_site, headers=headers, data=data, allow_redirects=True)) # Post login data
        y = check_response(r.get(confirmed_site, headers=headers, allow_redirects=True)) # Follow the next redirect
        z = bs(y.text, "html.parser") # Load page into BeautifulSoup
        state = z.find(id="state")['value'] # Pull state info from stream
        id_token = z.find(id="id_token")['value'] # Pull ID Token from stream
        data = {
          'state': state,
          'id_token': id_token
        }
        check_response(r.post(base_site, headers=headers, data=data)) # Post the state and id_token
        final_data = check_response(r.get(base_site, headers=headers)) # Get the main dashboard page
        page = bs(final_data.text, 'html.parser') # Get data into BS4
        bin_data = page.find_all("div", {"class": "binRow"}) # Strip the bin data rows
        # Iterate over each bin day and put into a dict
        for i in bin_data:
            t = i.get_text()
            name = re.findall(": .*", t)[0].replace(": ", '').replace("\r", '')
            bin_date = re.findall(".*:", t)[0].replace(":",'')
            self._attributes[name] = bin_date

        year = datetime.now().strftime("%Y")
        recycle_week = datetime.strptime(self._attributes['Recycling'] + " " + year, "%a %d %b %Y")

        if int(datetime.now().strftime('%W')) == int(recycle_week.strftime('%W')):
            self._state = "Recycle"
        else:
            self._state = "Organic"

        self._attributes['last_updated'] = str(date.today())
