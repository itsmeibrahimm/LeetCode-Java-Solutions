import re
from dataclasses import dataclass
from typing import Dict, Optional

STATSD_METRIC_FORMAT = re.compile(
    r"^(?P<stat_name>[a-zA-Z0-9-_.]+)(?P<tags>[a-zA-Z0-9-_.~=]+)?:(?P<stat_value>[0-9.]+)(|(?P<unit>\w+))(@(?P<rate>[0-9.]+))?"
)


def _tags_from_raw_metric(raw_tags: Optional[str]) -> Dict[str, str]:
    """
    extract tags from a raw statsd metric into a dict
    """
    raw_tags = raw_tags or ""

    tags = {}
    for tag in raw_tags.split("~"):
        if not tag:
            continue
        key_value = tag.split("=", 2)
        if len(key_value) < 2:
            continue
        key, value = key_value
        tags[key] = value
    return tags


@dataclass
class Stat:
    raw: str
    stat_name: str
    stat_value: float
    tags: Dict[str, str]
    unit: Optional[str]
    rate: Optional[float]


def parse_raw_stat(raw: str) -> Optional[Stat]:
    match = STATSD_METRIC_FORMAT.match(raw)
    if not match:
        return None
    stat_name, stat_value, unit, rate = match.group(
        "stat_name", "stat_value", "unit", "rate"
    )
    tags = _tags_from_raw_metric(match.group("tags"))
    return Stat(
        raw, stat_name, float(stat_value), tags, unit, float(rate) if rate else None
    )
