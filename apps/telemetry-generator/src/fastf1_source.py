import math
import os

import fastf1
import pandas as pd

from .config import Config


def load_telemetry_stream(config: Config) -> pd.DataFrame:
    """Load one session's car telemetry for the requested drivers, merged
    across drivers and sorted by session time so it can be replayed as a
    single interleaved event stream."""
    os.makedirs(config.cache_dir, exist_ok=True)
    fastf1.Cache.enable_cache(config.cache_dir)

    session = fastf1.get_session(config.year, config.grand_prix, config.session)
    session.load(laps=False, telemetry=True, weather=False, messages=False)

    if config.drivers is None:
        driver_numbers = list(session.drivers)
    else:
        driver_numbers = [session.get_driver(code)["DriverNumber"] for code in config.drivers]

    frames = []
    for number in driver_numbers:
        car_data = session.car_data[number].copy()
        car_data["DriverNumber"] = number
        car_data["DriverCode"] = session.get_driver(number)["Abbreviation"]
        frames.append(car_data)

    telemetry = pd.concat(frames, ignore_index=True)
    telemetry["SessionTimeSeconds"] = telemetry["SessionTime"].dt.total_seconds()
    telemetry.sort_values("SessionTimeSeconds", inplace=True, ignore_index=True)
    return telemetry


def row_to_record(row: pd.Series, session_key: str) -> dict:
    return {
        "session_key": session_key,
        "driver_number": str(row["DriverNumber"]),
        "driver_code": row["DriverCode"],
        "session_time_s": round(float(row["SessionTimeSeconds"]), 3),
        "speed_kph": _safe_float(row.get("Speed")),
        "throttle_pct": _safe_float(row.get("Throttle")),
        "brake": bool(row.get("Brake")),
        "n_gear": _safe_int(row.get("nGear")),
        "rpm": _safe_int(row.get("RPM")),
        "drs": _safe_int(row.get("DRS")),
        "is_injected_fault": False,
        "fault_type": None,
    }


def _safe_float(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def _safe_int(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return int(value)
