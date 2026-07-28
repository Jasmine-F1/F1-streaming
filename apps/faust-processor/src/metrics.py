from prometheus_client import Counter, Histogram

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
