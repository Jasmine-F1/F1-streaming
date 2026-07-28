from src.fastf1_source import _safe_float, _safe_int


def test_safe_float_handles_nan():
    assert _safe_float(float("nan")) is None


def test_safe_float_handles_none():
    assert _safe_float(None) is None


def test_safe_float_passes_through_value():
    assert _safe_float(12.5) == 12.5


def test_safe_int_handles_nan():
    assert _safe_int(float("nan")) is None


def test_safe_int_converts():
    assert _safe_int(7.0) == 7
