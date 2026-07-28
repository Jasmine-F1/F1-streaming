# telemetry-generator

Replays a historical F1 session (pulled via [FastF1](https://docs.fastf1.dev/))
onto Kafka as a simulated live telemetry feed. It is a replay bridge, not a
synthetic data generator: the values are real car telemetry, paced out on a
(speed-adjustable) timeline and optionally seeded with injected faults so the
downstream alerting rules have something to catch.

## Usage

```bash
pip install -r requirements.txt

# Validate the FastF1 pull + replay pacing without a Kafka broker:
python -m src.main --dry-run

# Publish to Kafka once a broker exists:
python -m src.main --kafka-bootstrap-servers localhost:9092

# Full grid, real-time pacing, with fault injection on:
python -m src.main --drivers ALL --speed 1 --inject-faults
```

## CLI flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `--year` | `2023` | Season year |
| `--gp` | `Bahrain` | Grand Prix name |
| `--session` | `R` | FP1/FP2/FP3/Q/R |
| `--drivers` | `VER,HAM,LEC` | Comma-separated driver codes, or `ALL` |
| `--speed` | `20.0` | Replay speed multiplier vs. real session time |
| `--inject-faults` | off | Randomly emit out-of-range values / delayed records |
| `--fault-rate` | `0.02` | Probability per record when faults are enabled |
| `--kafka-bootstrap-servers` | `localhost:9092` (or `KAFKA_BOOTSTRAP_SERVERS`) | Kafka broker(s) |
| `--topic` | `f1.telemetry` (or `KAFKA_TOPIC`) | Kafka topic |
| `--dry-run` | off | Print records to stdout instead of publishing |
| `--cache-dir` | `.fastf1-cache` | FastF1 local data cache |

## Message schema (`f1.telemetry`, key = driver number)

```json
{
  "session_key": "2023_bahrain_r",
  "driver_number": "44",
  "driver_code": "HAM",
  "session_time_s": 1234.56,
  "speed_kph": 289.0,
  "throttle_pct": 100.0,
  "brake": false,
  "n_gear": 7,
  "rpm": 11800,
  "drs": 12,
  "is_injected_fault": false,
  "fault_type": null,
  "emitted_at": "2026-07-21T12:34:56.789Z"
}
```

Status: implemented and verified end-to-end (Week 1, Day 1-2) against a
local `kind` + Bitnami Kafka deployment (`scripts/setup-local-cluster.sh`).

Note: the Kafka broker's `advertised.listeners` points at an in-cluster
DNS name, so publishing from the host via `kubectl port-forward` will hang.
Run the generator as an in-cluster pod (or, later, via its Helm chart)
pointing at `kafka.pipeline.svc.cluster.local:9092` instead.
