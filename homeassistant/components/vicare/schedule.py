"""Schedule helpers for the ViCare integration."""

from collections.abc import Callable, Mapping
from datetime import time
from typing import Any

from PyViCare.PyViCareUtils import PyViCareNotSupportedFeatureError

from homeassistant.const import ATTR_MODE
from homeassistant.core import ServiceResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import DOMAIN, VICARE_API_ERRORS
from .services import ATTR_FROM, ATTR_TO, WEEKDAYS


def _to_vicare_time(value: time) -> str:
    """Format a slot time for ViCare, which marks the end of the day as 24:00."""
    if value == time.max:
        return "24:00"
    return value.strftime("%H:%M")


def to_ha_schedule(
    schedule: Mapping[str, Any], vicare_to_ha_mode: Mapping[str, str]
) -> ServiceResponse:
    """Convert a ViCare schedule to the format of the schedule actions."""
    return {
        day: [
            {
                ATTR_FROM: f"{slot['start']}:00",
                ATTR_TO: f"{slot['end']}:00",
                ATTR_MODE: vicare_to_ha_mode[slot["mode"]],
            }
            for slot in sorted(schedule[day[:3]], key=lambda entry: entry["position"])
        ]
        for day in WEEKDAYS
    }


def to_vicare_schedule(
    current: Mapping[str, Any],
    slots_by_day: Mapping[str, list[dict[str, Any]]],
    ha_to_vicare_mode: Mapping[str, str],
) -> dict[str, Any]:
    """Convert slots to a ViCare schedule, keeping the current slots of other days."""
    schedule = {day[:3]: current[day[:3]] for day in WEEKDAYS}
    for day, slots in slots_by_day.items():
        schedule[day[:3]] = [
            {
                "start": _to_vicare_time(slot[ATTR_FROM]),
                "end": _to_vicare_time(slot[ATTR_TO]),
                "mode": ha_to_vicare_mode[slot[ATTR_MODE]],
                "position": position,
            }
            for position, slot in enumerate(slots)
        ]
    return schedule


def read_schedule_data[T](read: Callable[[], T], not_supported_key: str) -> T:
    """Read schedule data, translating unsupported features and API errors."""
    try:
        return read()
    except PyViCareNotSupportedFeatureError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key=not_supported_key,
        ) from err
    except VICARE_API_ERRORS as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="api_error",
        ) from err
