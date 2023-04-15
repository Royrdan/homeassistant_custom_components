"""Stock market information from Yahoo ."""
## custom_components.asx_tracker.sensor for debugging
from datetime import timedelta, datetime
import logging
from bs4 import BeautifulSoup
import requests
import voluptuous as vol
from time import sleep

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import ATTR_ATTRIBUTION, CONF_CURRENCY, CONF_NAME
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_ASX_CODE = "asx_code"
CONF_ASX_CODES = "asx_codes"
CONF_UNITS = "units"
CONF_PURCHASE_PRICE = "purchase_price"

SCAN_INTERVAL = timedelta(minutes=5)

ASX_CODE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_ASX_CODE): cv.string,
        vol.Required(CONF_UNITS): cv.positive_int,
        vol.Required(CONF_PURCHASE_PRICE): cv.positive_float,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_ASX_CODES): vol.All(cv.ensure_list, [ASX_CODE_SCHEMA]),
    }
)

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
url = "https://query2.finance.yahoo.com/v7/finance/options/{code}"
scrape_url = "https://finance.yahoo.com/quote/{code}/profile?ltr=1"
logo_base_url = "https://logo.clearbit.com/{webpage}?size=32"


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Alpha Vantage sensor."""
    asx_codes = config.get(CONF_ASX_CODES, [])

    dev = []
    for asx_code_data in asx_codes:
        _LOGGER.debug("Configuring stock: %s", asx_code_data[CONF_ASX_CODE])
        stock_data_obj = requests.get(  url.format(code=asx_code_data[CONF_ASX_CODE]), headers = headers  )
        if stock_data_obj.status_code == 200:
            if len(stock_data_obj.json()['optionChain']['result']) == 0:
                _LOGGER.error("Stock '%s' is invalid", asx_code_data[CONF_ASX_CODE])
            else:
                stock_data = stock_data_obj.json()['optionChain']['result'][0]['quote']
                dev.append(ASXSensor(stock_data, asx_code_data))
        else:
            _LOGGER.warning("Failed to retreive stock price for " + self._asx_code + " with error code " + str(data.status_code))

    add_entities(dev, True)


class ASXSensor(SensorEntity):
    """Representation of an ASX stock sensor."""

    def __init__(self, stock_data, asx_code_data):
        """Initialize the sensor."""
        self._name = "ASX " + asx_code_data[CONF_NAME]
        self._friendly_name = asx_code_data[CONF_NAME]
        self._asx_code = asx_code_data[CONF_ASX_CODE]
        self._units = asx_code_data[CONF_UNITS]
        self._purchase_price = asx_code_data[CONF_PURCHASE_PRICE]
        self._unit_of_measurement = "$"
        self._icon = None
        self._state = None
        self._purchase_value = self._purchase_price * self._units
        self._attributes = {
            "units": self._units,
            "purchase_price": self._purchase_price,
            "purchase_value": self._purchase_value
            }

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def friendly_name(self):
        """Return the friendly name of the sensor."""
        return self._friendly_name

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        return self._icon

    @property
    def extra_state_attributes(self):
        return self._attributes

    def update(self):
        """Get the latest data and updates the states."""
        response = 0
        count = 0
        while True:
            count += 1
            # Get data from API
            _LOGGER.debug("Reloading data for stock %s", self._name)
            data_obj = requests.get(  url.format(code=self._asx_code), headers = headers  )
            _LOGGER.debug( self._name + " has loaded " + str(count) + " time(s) with status code " + str(data_obj.status_code) )
            if count == 3 or data_obj.status_code == 200:
                _LOGGER.debug("Asked to BREAK as its all good")
                break
            else:
                _LOGGER.debug("Sleeping for 60 seconds")
                sleep(60)

        if data_obj.status_code == 200:
            data = data_obj.json()['optionChain']['result'][0]['quote']
            self._state = data['regularMarketPrice']
            market_value = round(self._state * self._units, 2)
            profit_total = round(market_value - self._purchase_value, 2)
            if datetime.today().hour < 12 and data['marketState'] == "CLOSED":
                profit_today = 0
            else:
                profit_today = round((self._units * data['regularMarketPrice']) - (self._units * data['regularMarketPreviousClose']), 2)
            self._attributes = {
                "profit_today": profit_today,
                "units": self._units,
                "purchase_price": self._purchase_price,
                "purchase_value": self._purchase_value,
                "market_value": market_value,
                "profit_total": profit_total,
                "long_name": data['longName'],
                "open_price": data['regularMarketOpen'],
                "current_bid": data['bid'],
                "todays_high": data['regularMarketDayHigh'],
                "todays_low": data['regularMarketDayLow'],
                "previous_close": data['regularMarketPreviousClose'],
                "50_day_average": data['fiftyDayAverage'],
                "200_day_average": data['twoHundredDayAverage'],
                "market_state": data['marketState'],
            }
        else:
            _LOGGER.warning("Failed to retreive stock price for " + self._asx_code + " with error code " + str(data.status_code))

        # Get data from Scraping. For ICON URL for now
        if self._icon == None:
          info_obj = requests.get(  scrape_url.format(code=self._asx_code), headers = headers)
          if info_obj.status_code == 200:
              soup = BeautifulSoup(info_obj.content, "html.parser")
              webpage_data = soup.select(selector = "#Col1-0-Profile-Proxy > section > div.asset-profile-container > div > div > p.D\(ib\).W\(47\.727\%\).Pend\(40px\)")
              try:
                  webpage = webpage_data[0].find_all("a")[-1].get('href')
              except:
                  _LOGGER.error("Failed to scrape profile information from the webpage for stock code " + self._asx_code)
              else:
                  domain = webpage.replace('https://', '').replace('http://', '').split('/')[0].replace('colesgroup', 'coles')
                  self._icon = logo_base_url.format(webpage=domain)
          else:
              _LOGGER.warning("Failed to retreive stock profile for " + self._asx_code + " with error code " + str(info_obj.status_code))
  
  

        _LOGGER.debug("Received new values for asx_code %s", self._asx_code)
