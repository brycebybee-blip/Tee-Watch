from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import requests

BASE = "https://foreupsoftware.com/index.php/api/booking/times"

HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


@dataclass(frozen=True)
class Slot:
    course_key: str
    course_name: str
    time: dt.datetime
    holes: int
    available_spots: int
    allowed_group_sizes: tuple[int, ...]

    def slot_id(self) -> str:
        return f"{self.course_key}|{self.time.isoformat()}|{self.holes}"


def fetch_slots(
    course_key: str,
    course_id: int,
    schedule_id: int,
    date: dt.date,
    session: requests.Session | None = None,
) -> list[Slot]:
    s = session or requests.Session()
    params = {
        "time": "all",
        "date": date.strftime("%m-%d-%Y"),
        "holes": "all",
        "players": 0,
        "schedule_id": schedule_id,
        "schedule_ids[]": schedule_id,
        "specials_only": 0,
        "api_key": "no_limits",
    }
    r = s.get(BASE, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    raw = r.json()
    return [
        Slot(
            course_key=course_key,
            course_name=item.get("schedule_name") or item.get("course_name", ""),
            time=dt.datetime.strptime(item["time"], "%Y-%m-%d %H:%M"),
            holes=int(item.get("holes", 0)),
            available_spots=int(item.get("available_spots", 0)),
            allowed_group_sizes=tuple(int(x) for x in item.get("allowed_group_sizes", [])),
        )
        for item in raw
    ]
