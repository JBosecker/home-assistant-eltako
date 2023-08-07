"""Support for Eltako events."""
from __future__ import annotations

from eltakobus.util import AddressExpression
from eltakobus.eep import *

from homeassistant.components.event import (
    PLATFORM_SCHEMA,
    EventEntity,
    EventEntityDescription,
    EventDeviceClass
)
from homeassistant import config_entries
from homeassistant.const import CONF_ID, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .device import EltakoEntity
from .const import CONF_ID_REGEX, CONF_EEP, DOMAIN, MANUFACTURER, DATA_ELTAKO, ELTAKO_CONFIG, ELTAKO_GATEWAY, LOGGER

DEPENDENCIES = ["eltakobus"]
EVENT_TYPE_BUTTON_PRESSED = "button_pressed"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Event platform for Eltako."""
    config: ConfigType = hass.data[DATA_ELTAKO][ELTAKO_CONFIG]
    gateway = hass.data[DATA_ELTAKO][ELTAKO_GATEWAY]
    
    entities: list[EltakoSensor] = []
    
    if Platform.EVENT in config:
        for entity_config in config[Platform.EVENT]:
            dev_id = AddressExpression.parse(entity_config.get(CONF_ID))
            dev_name = entity_config.get(CONF_NAME)
            eep_string = entity_config.get(CONF_EEP)

            try:
                dev_eep = EEP.find(eep_string)
            except:
                LOGGER.warning("Could not find EEP %s for device with address %s", eep_string, dev_id.plain_address())
                continue
            else:
                if dev_eep in [F6_02_01, F6_02_02]:
                    entities.append(EltakoEvent(gateway, dev_id, dev_name, dev_eep, EventDeviceClass.BUTTON, "A1"))
                    entities.append(EltakoEvent(gateway, dev_id, dev_name, dev_eep, EventDeviceClass.BUTTON, "A0"))
                    entities.append(EltakoEvent(gateway, dev_id, dev_name, dev_eep, EventDeviceClass.BUTTON, "B1"))
                    entities.append(EltakoEvent(gateway, dev_id, dev_name, dev_eep, EventDeviceClass.BUTTON, "B0"))


    async_add_entities(entities)
    

class EltakoEvent(EltakoEntity, EventEntity):
    """Representation of Eltako events such as wall switches.

    Supported EEPs (EnOcean Equipment Profiles):
    - F6-02-01 (Light and Blind Control - Application Style 1)
    - F6-02-02 (Light and Blind Control - Application Style 2)
    """

    def __init__(self, gateway, dev_id, dev_name, dev_eep, device_class, channel):
        """Initialize the Eltako event."""
        super().__init__(gateway, dev_id, dev_name)
        self._dev_eep = dev_eep
        self._attr_device_class = device_class
        self._attr_unique_id = f"{DOMAIN}_{dev_id.plain_address().hex()}_{device_class}_{channel}"
        self._attr_event_types = [EVENT_TYPE_BUTTON_PRESSED]
        self.entity_id = f"event.{self.unique_id}"
        self._channel = channel

    @property
    def name(self):
        """Return the default name for the event."""
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, self.dev_id.plain_address().hex())
            },
            name=self.dev_name,
            manufacturer=MANUFACTURER,
            model=self._dev_eep.eep_string,
            via_device=(DOMAIN, self.gateway.unique_id),
        )

    def value_changed(self, msg):
        """Fire an event with the data that have changed.

        This method is called when there is an incoming message associated
        with this platform.

        Example message data:
        - 2nd button pressed
            ['0xf6', '0x10', '0x00', '0x2d', '0xcf', '0x45', '0x30']
        - button released
            ['0xf6', '0x00', '0x00', '0x2d', '0xcf', '0x45', '0x20']
        """
        
        try:
            decoded = self._dev_eep.decode_message(msg)
        except Exception as e:
            LOGGER.warning("Could not decode message: %s", str(e))
            return
        
        if self._dev_eep in [F6_02_01, F6_02_02]:
            channel = self._channel
            first_action = decoded.rocker_first_action
            first_action_pressed = decoded.energy_bow == 1
            second_action = decoded.rocker_second_action
            second_action_pressed = decoded.second_action == 1
            
            if ((first_action == 0 && first_action_pressed) || (second_action == 0 && second_action_pressed)) && channel == "A1":
                self._trigger_event(EVENT_TYPE_BUTTON_PRESSED)
                self.async_write_ha_state()
            elif ((first_action == 1 && first_action_pressed) || (second_action == 1 && second_action_pressed)) && channel == "A0":
                self._trigger_event(EVENT_TYPE_BUTTON_PRESSED)
                self.async_write_ha_state()
            elif ((first_action == 2 && first_action_pressed) || (second_action == 2 && second_action_pressed)) && channel == "B1":
                self._trigger_event(EVENT_TYPE_BUTTON_PRESSED)
                self.async_write_ha_state()
            elif ((first_action == 3 && first_action_pressed) || (second_action == 3 && second_action_pressed)) && channel == "B0":
                self._trigger_event(EVENT_TYPE_BUTTON_PRESSED)
                self.async_write_ha_state()
            else:
                return
