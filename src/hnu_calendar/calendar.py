from datetime import datetime, timezone
from typing import Iterable, List, Optional, Sequence

from .models import CalendarEvent


def _escape(value: str) -> str:
    return (value.replace("\\", "\\\\").replace("\n", "\\n")
            .replace(";", "\\;").replace(",", "\\,"))


def _fold(line: str) -> List[str]:
    result = []
    remaining = line
    first = True
    while remaining:
        limit = 75 if first else 74
        size = 0
        cut = 0
        for index, char in enumerate(remaining):
            width = len(char.encode("utf-8"))
            if size + width > limit:
                break
            size += width
            cut = index + 1
        if cut == 0:
            cut = 1
        result.append(("" if first else " ") + remaining[:cut])
        remaining = remaining[cut:]
        first = False
    return result or [""]


def render_ics(
    events: Iterable[CalendarEvent],
    calendar_name: str,
    timezone_name: str,
    alert_times: Sequence[int],
    now: Optional[datetime] = None,
) -> str:
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//HNU Course Calendar//ZH-CN",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        "X-WR-CALNAME:%s" % _escape(calendar_name),
        "X-WR-TIMEZONE:%s" % timezone_name,
        "BEGIN:VTIMEZONE", "TZID:%s" % timezone_name,
        "X-LIC-LOCATION:%s" % timezone_name,
        "BEGIN:STANDARD", "TZOFFSETFROM:+0800", "TZOFFSETTO:+0800",
        "TZNAME:CST", "DTSTART:19700101T000000", "END:STANDARD", "END:VTIMEZONE",
    ]
    for event in events:
        lines.extend([
            "BEGIN:VEVENT", "UID:%s" % event.uid,
            "DTSTAMP:%s" % stamp,
            "LAST-MODIFIED:%s" % stamp,
            "DTSTART;TZID=%s:%s" % (timezone_name, event.start.strftime("%Y%m%dT%H%M%S")),
            "DTEND;TZID=%s:%s" % (timezone_name, event.end.strftime("%Y%m%dT%H%M%S")),
            "SUMMARY:%s" % _escape(event.name),
            "LOCATION:%s" % _escape(event.location),
            "DESCRIPTION:%s" % _escape(event.description),
            "SEQUENCE:%d" % event.sequence,
        ])
        for minutes in alert_times:
            lines.extend([
                "BEGIN:VALARM", "ACTION:DISPLAY",
                "DESCRIPTION:%s" % _escape(event.name),
                "TRIGGER:-PT%dM" % int(minutes), "END:VALARM",
            ])
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    folded = [part for line in lines for part in _fold(line)]
    return "\r\n".join(folded) + "\r\n"
