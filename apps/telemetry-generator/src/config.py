import argparse
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    year: int
    grand_prix: str
    session: str
    drivers: Optional[list]  # None means every driver in the session
    speed: float
    inject_faults: bool
    fault_rate: float
    kafka_bootstrap_servers: str
    topic: str
    dry_run: bool
    cache_dir: str


def parse_args(argv=None) -> Config:
    parser = argparse.ArgumentParser(
        description="Replay FastF1 historical telemetry onto Kafka as a simulated live feed."
    )
    parser.add_argument("--year", type=int, default=2023)
    parser.add_argument("--gp", dest="grand_prix", default="Bahrain")
    parser.add_argument("--session", default="R", help="FP1/FP2/FP3/Q/R")
    parser.add_argument(
        "--drivers",
        default="VER,HAM,LEC",
        help="Comma-separated driver codes (e.g. VER,HAM), or ALL for the full grid",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=20.0,
        help="Replay speed multiplier vs. real session time (1.0 = real time)",
    )
    parser.add_argument("--inject-faults", action="store_true")
    parser.add_argument(
        "--fault-rate",
        type=float,
        default=0.02,
        help="Probability per record of injecting an out-of-range value or a delay",
    )
    parser.add_argument(
        "--kafka-bootstrap-servers",
        default=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    )
    parser.add_argument("--topic", default=os.environ.get("KAFKA_TOPIC", "f1.telemetry"))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print records to stdout instead of publishing to Kafka",
    )
    parser.add_argument(
        "--cache-dir", default=os.environ.get("FASTF1_CACHE_DIR", ".fastf1-cache")
    )

    args = parser.parse_args(argv)
    drivers = None if args.drivers.upper() == "ALL" else [
        d.strip().upper() for d in args.drivers.split(",")
    ]

    return Config(
        year=args.year,
        grand_prix=args.grand_prix,
        session=args.session,
        drivers=drivers,
        speed=args.speed,
        inject_faults=args.inject_faults,
        fault_rate=args.fault_rate,
        kafka_bootstrap_servers=args.kafka_bootstrap_servers,
        topic=args.topic,
        dry_run=args.dry_run,
        cache_dir=args.cache_dir,
    )
