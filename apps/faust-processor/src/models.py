from typing import List, Optional

import faust


class TelemetryRecord(faust.Record, serializer="json"):
    """Matches the JSON payload published by apps/telemetry-generator."""

    session_key: str
    driver_number: str
    driver_code: str
    session_time_s: float
    brake: bool
    is_injected_fault: bool
    emitted_at: str
    speed_kph: Optional[float] = None
    throttle_pct: Optional[float] = None
    n_gear: Optional[int] = None
    rpm: Optional[int] = None
    drs: Optional[int] = None
    fault_type: Optional[str] = None


class ProcessedTelemetryRecord(faust.Record, serializer="json"):
    """TelemetryRecord plus validation results and derived features."""

    session_key: str
    driver_number: str
    driver_code: str
    session_time_s: float
    brake: bool
    is_injected_fault: bool
    emitted_at: str
    is_valid: bool
    validation_errors: List[str]
    out_of_order: bool
    processed_at: str
    pipeline_lag_s: float
    speed_kph: Optional[float] = None
    throttle_pct: Optional[float] = None
    n_gear: Optional[int] = None
    rpm: Optional[int] = None
    drs: Optional[int] = None
    fault_type: Optional[str] = None
    speed_delta_kph: Optional[float] = None
