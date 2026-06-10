from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import yaml

from adapters import foreup
from notify import send_email

ROOT = Path(__file__).parent
SEEN_PATH = ROOT / "seen.json"

DOW = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}


def load_yaml(name: str) -> dict:
    with open(ROOT / name) as f:
        return yaml.safe_load(f)


def load_seen() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    return set(json.loads(SEEN_PATH.read_text()))


def save_seen(seen: set[str]) -> None:
    SEEN_PATH.write_text(json.dumps(sorted(seen), indent=2))


def slot_matches(slot: foreup.Slot, f: dict) -> bool:
    dow_allowed = f.get("days_of_week", "all")
    if dow_allowed != "all":
        allowed = {DOW[d] for d in dow_allowed}
        if slot.time.weekday() not in allowed:
            return False

    tw = f.get("time_window")
    if tw:
        start = dt.time.fromisoformat(tw["start"])
        end = dt.time.fromisoformat(tw["end"])
        if not (start <= slot.time.time() <= end):
            return False

    if slot.available_spots < f.get("min_available_spots", 1):
        return False

    holes = f.get("holes", "any")
    if holes != "any" and slot.holes != int(holes):
        return False

    return True


def fetch_for_course(key: str, cfg: dict, date_range: tuple[int, int]) -> list[foreup.Slot]:
    if cfg["provider"] != "foreup":
        raise ValueError(f"Unknown provider: {cfg['provider']}")
    today = dt.date.today()
    slots = []
    for offset in range(date_range[0], date_range[1] + 1):
        date = today + dt.timedelta(days=offset)
        slots.extend(
            foreup.fetch_slots(
                course_key=key,
                course_id=cfg["course_id"],
                schedule_id=cfg["schedule_id"],
                date=date,
            )
        )
    return slots


def render_email(new_slots: list[foreup.Slot], courses: dict) -> tuple[str, str]:
    lines = []
    for s in sorted(new_slots, key=lambda x: (x.course_key, x.time)):
        name = courses[s.course_key]["display_name"]
        lines.append(
            f"<li><b>{name}</b> — {s.time.strftime('%a %b %d, %I:%M %p')} "
            f"· {s.holes} holes · {s.available_spots} spot(s)</li>"
        )
    subject = f"[tee-watch] {len(new_slots)} new slot(s) at "
    subject += ", ".join(sorted({courses[s.course_key]["display_name"] for s in new_slots}))
    html = "<ul>" + "".join(lines) + "</ul>"
    return subject, html


def main() -> int:
    courses = load_yaml("courses.yml")
    filters = load_yaml("filters.yml")
    date_range = tuple(filters.get("date_range_days", [1, 7]))

    selected = filters.get("courses") or list(courses.keys())
    all_slots: list[foreup.Slot] = []
    for key in selected:
        all_slots.extend(fetch_for_course(key, courses[key], date_range))

    matched = [s for s in all_slots if slot_matches(s, filters)]
    print(f"Fetched {len(all_slots)} slots; {len(matched)} match filters.")

    seen = load_seen()
    new_ids = {s.slot_id() for s in matched} - seen
    new_slots = [s for s in matched if s.slot_id() in new_ids]

    if new_slots:
        print(f"{len(new_slots)} new — sending notification.")
        subject, html = render_email(new_slots, courses)
        if "--dry-run" in sys.argv:
            print(subject)
            print(html)
        else:
            send_email(subject, html)
    else:
        print("No new slots.")

    save_seen({s.slot_id() for s in matched})
    return 0


if __name__ == "__main__":
    sys.exit(main())
