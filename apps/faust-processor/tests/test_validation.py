from src.models import TelemetryRecord
from src.validation import validate


def _record(**overrides):
    base = dict(
        session_key="test",
        driver_number="1",
        driver_code="VER",
        session_time_s=1.0,
        brake=False,
        is_injected_fault=False,
        emitted_at="2026-01-01T00:00:00+00:00",
        speed_kph=300.0,
        throttle_pct=100.0,
        n_gear=7,
        rpm=11000,
        drs=0,
    )
    base.update(overrides)
    return TelemetryRecord(**base)


def test_valid_record_has_no_errors():
    assert validate(_record()) == []


def test_real_sensor_throttle_overshoot_is_not_flagged():
    # FastF1 has been observed reporting >100% throttle in practice
    # (confirmed during the Day 1-2 dry-run) — the bound has margin for this.
    assert validate(_record(throttle_pct=104.0)) == []


def test_out_of_range_speed_is_flagged():
    assert "speed_out_of_range" in validate(_record(speed_kph=1000.0))


def test_out_of_range_rpm_is_flagged():
    assert "rpm_out_of_range" in validate(_record(rpm=99000))


def test_missing_speed_is_flagged():
    assert "speed_out_of_range" in validate(_record(speed_kph=None))
