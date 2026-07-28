import random

FAULT_TYPES = ("out_of_range", "delay")


def maybe_inject_fault(record: dict, rate: float):
    """With probability `rate`, mutate a copy of `record` into a fault case.

    Returns (record, extra_delay_seconds) — extra_delay_seconds is additional
    sleep to apply before publishing, used to simulate late-arriving data.
    """
    if random.random() >= rate:
        return record, 0.0

    fault_type = random.choice(FAULT_TYPES)
    record = dict(record)
    record["is_injected_fault"] = True
    record["fault_type"] = fault_type

    if fault_type == "out_of_range":
        field = random.choice(["speed_kph", "rpm"])
        current = record.get(field) or 0
        record[field] = current * random.uniform(5, 10) + 1000
        return record, 0.0

    # "delay": leave the payload untouched, just hold it before publishing
    return record, random.uniform(3.0, 10.0)
