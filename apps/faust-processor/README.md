# faust-processor

Consumes `f1.telemetry` (published by `apps/telemetry-generator`), validates
each record against physically-plausible bounds, computes a couple of
per-driver derived features, and republishes the result to
`f1.telemetry.processed`. Exposes Prometheus-format metrics for Grafana/
Alertmanager to consume later.

Built on [faust-streaming](https://github.com/faust-streaming/faust) — the
maintained fork of the original (now-dormant) `faust` package.

## Usage

```bash
pip install -r requirements.txt

# Runs as a long-lived worker, not a one-shot script:
python -m src.app worker -l info
```

Configuration is via environment variables (no CLI flags, since Faust's own
`worker` subcommand owns argv):

| Env var | Default | Meaning |
| --- | --- | --- |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka.pipeline.svc.cluster.local:9092` | Kafka broker(s) |
| `INPUT_TOPIC` | `f1.telemetry` | Topic to consume |
| `OUTPUT_TOPIC` | `f1.telemetry.processed` | Topic to publish validated/enriched records to |
| `FAUST_APP_ID` | `f1-faust-processor` | Consumer group / app id |
| `FAUST_WEB_PORT` | `6066` | Port serving Faust's web UI and `/metrics` |

## What it does per record

1. **Validate**: `speed_kph` / `rpm` / `throttle_pct` against plausibility
   bounds (`src/config.py`) — wide enough to tolerate real FastF1 sensor
   quirks (e.g. throttle occasionally reads >100%), tight enough that
   injected faults (which overshoot by design) still get caught.
2. **Feature engineering** (stateful, per `driver_number`, via Faust Tables
   backed by in-memory storage — state resets on pod restart, which is fine
   for a demo but would move to RocksDB/external store for anything more):
   - `speed_delta_kph`: change vs. the driver's previous sample
   - `out_of_order`: true if this record's `session_time_s` trails behind
     the max already seen for that driver — the signal for the `delay`
     fault type from the generator (also legitimately fires if you run two
     separate generator sessions back-to-back into the same topic, since
     session time resets)
3. **Publish** a `ProcessedTelemetryRecord` (`src/models.py`) to
   `OUTPUT_TOPIC`, plus Prometheus counters/histogram (`src/metrics.py`).

## Metrics (`GET /metrics`)

- `f1_telemetry_records_total{driver_code}` — counter
- `f1_telemetry_invalid_total{driver_code, reason}` — counter
- `f1_telemetry_out_of_order_total{driver_code}` — counter
- `f1_telemetry_pipeline_lag_seconds` — histogram of wall-clock
  `now() - emitted_at`

## Verified

Ran in-cluster against a live `telemetry-generator` (with `--inject-faults`):
raw (`f1.telemetry`) and processed (`f1.telemetry.processed`) topic offsets
matched exactly at every check, including mid-stream — zero message loss,
zero duplication. Confirmed `is_valid:false` fires on injected out-of-range
values, `out_of_order:true` fires on injected delays, and `/metrics` updates
live as records flow through.

Status: implemented and verified end-to-end (Week 2 start). Not yet
Dockerized into a Helm chart for continuous deployment — currently run as a
one-off pod for verification, same as `telemetry-generator` at this stage.
