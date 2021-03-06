import logging

from homeassistant.components import persistent_notification
from homeassistant.components.remote import ATTR_DEVICE
from homeassistant.helpers.entity import ToggleEntity

from . import DOMAIN, Gateway3Device
from .gateway3 import Gateway3

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        async_add_entities([Gateway3Entity(gateway, device, attr)])

    gw: Gateway3 = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup('remote', setup)


class Gateway3Entity(Gateway3Device, ToggleEntity):
    _state = False

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        if self.gw.zha and not self.hass.config_entries.async_entries('zha'):
            persistent_notification.async_create(
                self.hass,
                "Integration: **Zigbee Home Automation**\n"
                "Radio Type: **EZSP**\n"
                f"Path: `socket://{self.gw.host}:8888`\n"
                "Speed: `115200`", "Please create manually")

    @property
    def is_on(self) -> bool:
        return self._state

    @property
    def state_attributes(self):
        return self._attrs

    @property
    def icon(self):
        return 'mdi:zigbee'

    def update(self, data: dict = None):
        if 'pairing_start' in data:
            self._state = True

        elif 'pairing_stop' in data:
            self._state = False
            self.gw.pair_model = None

        elif 'added_device' in data:
            text = "New device:\n" + '\n'.join(
                f"{k}: {v}" for k, v in data['added_device'].items()
            )
            persistent_notification.async_create(self.hass, text,
                                                 "Xiaomi Gateway 3")

        elif 'network_pan_id' in data:
            self._attrs.update(data)

        self.schedule_update_ha_state()

    def turn_on(self):
        self.gw.send(self.device, {'pairing_start': 60})

    def turn_off(self):
        self.gw.send(self.device, {'pairing_stop': 0})

    async def async_send_command(self, command, **kwargs):
        for cmd in command:
            # for testing purposes
            if cmd == 'ble':
                raw = kwargs[ATTR_DEVICE].replace('\'', '"')
                self.gw.process_ble_event(raw)
            elif cmd == 'pair':
                model: str = kwargs[ATTR_DEVICE]
                self.gw.pair_model = (model[:-3] if model.endswith('.v1')
                                      else model)
                self.turn_on()
            elif cmd == 'reboot':
                self.gw.send_telnet('reboot')
            elif cmd == 'publishstate':
                self.gw.send_mqtt('publishstate')
