import json
import sys


class StdoutSink:
    def send(self, key: str, record: dict) -> None:
        print(json.dumps({"key": key, **record}), file=sys.stdout, flush=True)

    def flush(self) -> None:
        pass


class KafkaSink:
    def __init__(self, bootstrap_servers: str, topic: str):
        from confluent_kafka import Producer  # imported lazily so --dry-run needs no broker/lib setup

        self._topic = topic
        self._producer = Producer({"bootstrap.servers": bootstrap_servers})

    def send(self, key: str, record: dict) -> None:
        self._producer.produce(
            self._topic,
            key=key.encode("utf-8"),
            value=json.dumps(record).encode("utf-8"),
        )
        self._producer.poll(0)

    def flush(self) -> None:
        self._producer.flush()
