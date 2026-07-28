import sys
import time
from datetime import datetime, timezone

from .config import Config
from .fastf1_source import load_telemetry_stream, row_to_record
from .faults import maybe_inject_fault
from .sinks import KafkaSink, StdoutSink


def run(config: Config) -> None:
    session_key = f"{config.year}_{config.grand_prix}_{config.session}".lower().replace(" ", "_")
    telemetry = load_telemetry_stream(config)

    sink = StdoutSink() if config.dry_run else KafkaSink(config.kafka_bootstrap_servers, config.topic)

    prev_time_s = None
    emitted = 0
    try:
        for _, row in telemetry.iterrows():
            record = row_to_record(row, session_key)

            extra_delay = 0.0
            if config.inject_faults:
                record, extra_delay = maybe_inject_fault(record, config.fault_rate)

            if prev_time_s is not None:
                wait = max(0.0, (record["session_time_s"] - prev_time_s) / config.speed)
                time.sleep(wait)
            prev_time_s = record["session_time_s"]

            if extra_delay:
                time.sleep(extra_delay)

            record["emitted_at"] = datetime.now(timezone.utc).isoformat()
            sink.send(record["driver_number"], record)

            emitted += 1
            if emitted % 500 == 0:
                print(f"[telemetry-generator] emitted {emitted} records", file=sys.stderr)
    finally:
        sink.flush()

    print(f"[telemetry-generator] done, emitted {emitted} records total", file=sys.stderr)
