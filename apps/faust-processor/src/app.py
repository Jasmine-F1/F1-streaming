from datetime import datetime, timezone

import faust
from prometheus_client import generate_latest

from . import config, metrics
from .models import ProcessedTelemetryRecord, TelemetryRecord
from .validation import validate

app = faust.App(
    config.APP_ID,
    broker=f"kafka://{config.KAFKA_BOOTSTRAP_SERVERS}",
    store="memory://",  # in-memory table state: fine for a local demo, does not
    # survive a pod restart. Would move to RocksDB (or an external store) for
    # anything beyond a portfolio demo.
    web_port=config.WEB_PORT,
)

raw_topic = app.topic(config.INPUT_TOPIC, key_type=str, value_type=TelemetryRecord)
processed_topic = app.topic(config.OUTPUT_TOPIC, key_type=str, value_type=ProcessedTelemetryRecord)

# Per-driver state, keyed by driver_number.
last_speed_kph = app.Table("last-speed-kph", default=float, partitions=1)
max_session_time_s = app.Table("max-session-time-s", default=float, partitions=1)


@app.agent(raw_topic)
async def process(records):
    async for key, record in records.items():
        errors = validate(record)
        is_valid = not errors

        prev_max_time = max_session_time_s[key]
        out_of_order = record.session_time_s < prev_max_time - config.OUT_OF_ORDER_SLACK_S
        if record.session_time_s > prev_max_time:
            max_session_time_s[key] = record.session_time_s

        prev_speed = last_speed_kph.get(key)
        speed_delta_kph = None
        if record.speed_kph is not None and prev_speed is not None:
            speed_delta_kph = record.speed_kph - prev_speed
        if record.speed_kph is not None:
            last_speed_kph[key] = record.speed_kph

        now = datetime.now(timezone.utc)
        pipeline_lag_s = (now - datetime.fromisoformat(record.emitted_at)).total_seconds()

        metrics.RECORDS_TOTAL.labels(driver_code=record.driver_code).inc()
        for reason in errors:
            metrics.INVALID_TOTAL.labels(driver_code=record.driver_code, reason=reason).inc()
        if out_of_order:
            metrics.OUT_OF_ORDER_TOTAL.labels(driver_code=record.driver_code).inc()
        metrics.PIPELINE_LAG_SECONDS.observe(max(pipeline_lag_s, 0.0))

        await processed_topic.send(
            key=key,
            value=ProcessedTelemetryRecord(
                session_key=record.session_key,
                driver_number=record.driver_number,
                driver_code=record.driver_code,
                session_time_s=record.session_time_s,
                brake=record.brake,
                is_injected_fault=record.is_injected_fault,
                emitted_at=record.emitted_at,
                is_valid=is_valid,
                validation_errors=errors,
                out_of_order=out_of_order,
                processed_at=now.isoformat(),
                pipeline_lag_s=pipeline_lag_s,
                speed_kph=record.speed_kph,
                throttle_pct=record.throttle_pct,
                n_gear=record.n_gear,
                rpm=record.rpm,
                drs=record.drs,
                fault_type=record.fault_type,
                speed_delta_kph=speed_delta_kph,
            ),
        )


@app.page("/metrics")
async def get_metrics(self, request):
    # Faust's Response wrapper rejects a content_type with "charset=" already
    # in it (it appends its own) — prometheus_client's CONTENT_TYPE_LATEST
    # includes one, so pass just the media type.
    return self.text(generate_latest().decode("utf-8"), content_type="text/plain")


if __name__ == "__main__":
    app.main()
