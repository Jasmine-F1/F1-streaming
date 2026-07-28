from src.faults import maybe_inject_fault


def _record():
    return {
        "speed_kph": 300.0,
        "rpm": 11000,
        "is_injected_fault": False,
        "fault_type": None,
    }


def test_no_fault_when_rate_zero():
    record = _record()
    result, delay = maybe_inject_fault(record, rate=0.0)
    assert result == record
    assert delay == 0.0


def test_fault_always_fires_when_rate_one():
    record = _record()
    result, delay = maybe_inject_fault(record, rate=1.0)
    assert result["is_injected_fault"] is True
    assert result["fault_type"] in ("out_of_range", "delay")
    if result["fault_type"] == "out_of_range":
        assert result["speed_kph"] > record["speed_kph"] or result["rpm"] > record["rpm"]
    else:
        assert delay > 0.0
