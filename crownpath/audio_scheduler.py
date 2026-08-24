from datetime import datetime
from crownpath.audio_service import schedules_for_zone

def active_schedule_for_zone(zone_id: str, now: datetime | None = None):
    now = now or datetime.now()
    weekday = now.strftime("%A").upper()
    hhmm = now.strftime("%H:%M")

    matches = []
    for item in schedules_for_zone(zone_id):
        if not item["enabled"]:
            continue
        if item["day_of_week"] != weekday:
            continue
        if item["start_time"] <= hhmm < item["end_time"]:
            matches.append(item)

    return matches[0] if matches else None
