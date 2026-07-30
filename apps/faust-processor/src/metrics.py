from prometheus_client import Counter, Gauge, Histogram

RECORDS_TOTAL = Counter(
    "f1_telemetry_records_total",
    "Telemetry records consumed from the raw topic",
    ["driver_code"],
)

INVALID_TOTAL = Counter(
    "f1_telemetry_invalid_total",
    "Records that failed a validation rule",
    ["driver_code", "reason"],
)

OUT_OF_ORDER_TOTAL = Counter(
    "f1_telemetry_out_of_order_total",
    "Records that arrived out of session-time order for their driver (late data)",
    ["driver_code"],
)

PIPELINE_LAG_SECONDS = Histogram(
    "f1_telemetry_pipeline_lag_seconds",
    "Wall-clock seconds between the producer emitting a record and Faust processing it",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)

# Gauges (not counters): these track the *current* value of a live signal, for
# the Grafana "mission control" telemetry panels — not pipeline-health
# bookkeeping like the metrics above.
SPEED_KPH = Gauge("f1_telemetry_speed_kph", "Most recent speed reading", ["driver_code"])
THROTTLE_PCT = Gauge("f1_telemetry_throttle_pct", "Most recent throttle reading", ["driver_code"])
RPM = Gauge("f1_telemetry_rpm", "Most recent RPM reading", ["driver_code"])
GEAR = Gauge("f1_telemetry_gear", "Most recent gear", ["driver_code"])
