"""Support for Eltako binary sensors."""
from __future__ import annotations

from eltakobus.util import AddressExpression
from eltakobus.eep import *

from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA,
    PLATFORM_SCHEMA,
    BinarySensorEntity,
)
from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE_CLASS, CONF_ID, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .device import EltakoEntity
from .const import CONF_ID_REGEX, CONF_EEP, DOMAIN, MANUFACTURER, DATA_ELTAKO, ELTAKO_CONFIG, ELTAKO_GATEWAY, LOGGER

DEPENDENCIES = ["eltakobus"]
EVENT_BUTTON_PRESSED = "button_pressed"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Binary Sensor platform for Eltako."""
    config: ConfigType = hass.data[DATA_ELTAKO][ELTAKO_CONFIG]
    gateway = hass.data[DATA_ELTAKO][ELTAKO_GATEWAY]
    
    entities: list[EltakoSensor] = []
    
    if Platform.BINARY_SENSOR in config:
        for entity_config in config[Platform.BINARY_SENSOR]:
            dev_id = AddressExpression.parse(entity_config.get(CONF_ID))
            dev_name = entity_config.get(CONF_NAME)
            device_class = entity_config.get(CONF_DEVICE_CLASS)
            eep_string = entity_config.get(CONF_EEP)

            try:
                dev_eep = EEP.find(eep_string)
            except:
                LOGGER.warning("Could not find EEP %s for device with address %s", eep_string, dev_id.plain_address())
                continue
            else:
                entities.append(EltakoBinarySensor(gateway, dev_id, dev_name, dev_eep, device_class))


    async_add_entities(entities)
    

class EltakoBinarySensor(EltakoEntity, BinarySensorEntity):
    """Representation of Eltako binary sensors such as motion sensors or window handles.

    Supported EEPs (EnOcean Equipment Profiles):
    - F6-10-00
    - D5-00-01
    - A5-08-01
    """

    def __init__(self, gateway, dev_id, dev_name, dev_eep, device_class):
        """Initialize the Eltako binary sensor."""
        super().__init__(gateway, dev_id, dev_name)
        self._dev_eep = dev_eep
        self._attr_device_class = device_class
        self._attr_unique_id = f"{DOMAIN}_{dev_id.plain_address().hex()}_{device_class}"
        self.entity_id = f"binary_sensor.{self.unique_id}"

    @property
    def name(self):
        """Return the default name for the binary sensor."""
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
        try:
            decoded = self._dev_eep.decode_message(msg)
        except Exception as e:
            LOGGER.warning("Could not decode message: %s", str(e))
            return
            
        if self._dev_eep in [F6_10_00]:
            action = (decoded.movement & 0x70) >> 4
            
            if action == 0x07:
                self._attr_is_on = False
            elif action in (0x04, 0x06):
                self._attr_is_on = False
            else:
                return

            self.schedule_update_ha_state()
        elif self._dev_eep in [D5_00_01]:
            if decoded.learn_button == 0:
                return
            
            self._attr_is_on = decoded.contact == 0

            self.schedule_update_ha_state()
        elif self._dev_eep in [A5_08_01]:
            if decoded.learn_button == 0:
                return
                
            self._attr_is_on = decoded.pir_status == 0
            
            self.schedule_update_ha_state()

