from typing import List

from . import config
from .models import TelemetryRecord


def validate(record: TelemetryRecord) -> List[str]:
    errors = []

    if record.speed_kph is None or not (0 <= record.speed_kph <= config.SPEED_MAX_KPH):
        errors.append("speed_out_of_range")

    if record.rpm is None or not (0 <= record.rpm <= config.RPM_MAX):
        errors.append("rpm_out_of_range")

    if record.throttle_pct is None or not (0 <= record.throttle_pct <= config.THROTTLE_MAX_PCT):
        errors.append("throttle_out_of_range")

    return errors
