import os


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


KAFKA_BOOTSTRAP_SERVERS = _env("KAFKA_BOOTSTRAP_SERVERS", "kafka.pipeline.svc.cluster.local:9092")
INPUT_TOPIC = _env("INPUT_TOPIC", "f1.telemetry")
OUTPUT_TOPIC = _env("OUTPUT_TOPIC", "f1.telemetry.processed")
APP_ID = _env("FAUST_APP_ID", "f1-faust-processor")
WEB_PORT = int(_env("FAUST_WEB_PORT", "6066"))

# Plausibility bounds for validation. Real FastF1 sensor data can slightly
# overshoot 100% throttle (observed 104.0 in practice), so these have a
# margin above the physically "clean" range rather than being a hard cap —
# injected faults (+1000 minimum) blow past them regardless.
SPEED_MAX_KPH = 380.0
RPM_MAX = 15000
THROTTLE_MAX_PCT = 110.0

# How far (in session-time seconds) a record can trail behind the latest
# session_time_s already seen for that driver before it's flagged as a
# late/out-of-order arrival.
OUT_OF_ORDER_SLACK_S = 0.5
