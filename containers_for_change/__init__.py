
import requests
import voluptuous as vol
from jinja2 import Template
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service
from .containers_for_change.cfc import containers_for_change

DOMAIN = "containers_for_change"
SERVICE_BOOK_COLLECTION = "book_collection"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required("username"): cv.string,
                vol.Required("password"): cv.string,
                vol.Required("address"): cv.string,
                vol.Required("suburb"): cv.string,
                vol.Required("postcode"): cv.string,
                vol.Required("mobile"): cv.string,
                vol.Required("bag_location"): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up the my_component component."""
    if DOMAIN not in config:
        return True

    async def book_collection_service_handler(service):
        """Handle the book_collection service."""

        template = Template(service.data.get("template", "{{ bags }}"))
        rendered_template = template.render(
            hass=hass,  # pass the hass object to the template
            **service.data,  # pass any additional inputs to the template
        )

        try:
            # try to render the template as an integer
            bags = int(rendered_template.strip())
        except ValueError:
            # if the template cannot be rendered as an integer, try to get the state of an entity
            entity_id = rendered_template.strip()
            if entity_id.startswith("sensor.") or entity_id.startswith("input_number."):
                # if the entity is a sensor or input_number, get the state using the states attribute
                entity_state = hass.states.get(entity_id)
                if entity_state is None:
                    raise vol.Invalid(f"Entity not found: {entity_id}")
                bags = int(entity_state.state)
            else:
                # if the entity is not a sensor or input_number, raise a validation error
                raise vol.Invalid("Invalid value for bags")


        username = hass.data[DOMAIN]["username"]
        password = hass.data[DOMAIN]["password"]
        address = hass.data[DOMAIN]["address"]
        suburb = hass.data[DOMAIN]["suburb"]
        postcode = hass.data[DOMAIN]["postcode"]
        mobile = hass.data[DOMAIN]["mobile"]
        bag_location = hass.data[DOMAIN]["bag_location"]

        cfc = containers_for_change(
            username = username,
            password = password,
            address = address,
            suburb = suburb,
            postcode = postcode,
            mobile = mobile,
            bag_location = bag_location,
        )

        booking_id, message = await hass.async_add_executor_job( cfc.book_collection, bags )

        if booking_id:
            hass.bus.async_fire(
                f"{DOMAIN}_{SERVICE_BOOK_COLLECTION}_success", {"Booking ID": booking_id}
            )
        else:
            hass.bus.async_fire(
                f"{DOMAIN}_{SERVICE_BOOK_COLLECTION}_failure", {"response": message}
            )

    hass.data[DOMAIN] = config[DOMAIN]
    async_register_admin_service(hass, DOMAIN, SERVICE_BOOK_COLLECTION, book_collection_service_handler, schema=vol.Schema(
        {vol.Required("bags"): cv.positive_int}
    ))

    return True
