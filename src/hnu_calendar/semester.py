from dataclasses import replace
from datetime import date, datetime, time, timedelta
from typing import Dict, Iterable, List, Tuple
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from .models import Adjustment, CalendarEvent, CourseBlock


PERIOD_TIMES: Dict[int, Tuple[time, time]] = {
    1: (time(7, 40), time(8, 25)),
    2: (time(8, 35), time(9, 20)),
    3: (time(9, 45), time(10, 30)),
    4: (time(10, 40), time(11, 25)),
    5: (time(14, 30), time(15, 15)),
    6: (time(15, 25), time(16, 10)),
    7: (time(16, 35), time(17, 20)),
    8: (time(17, 30), time(18, 15)),
    9: (time(19, 20), time(20, 5)),
    10: (time(20, 15), time(21, 0)),
    11: (time(21, 10), time(21, 55)),
}

SPECIAL_BLOCKS = {
    (12, 13): (time(11, 35), time(13, 5)),
    (14, 15): (time(13, 5), time(14, 20)),
}


def resolve_period_times(periods: Tuple[int, ...]) -> Tuple[time, time]:
    if periods in SPECIAL_BLOCKS:
        return SPECIAL_BLOCKS[periods]
    if not periods or periods[0] not in PERIOD_TIMES or periods[-1] not in PERIOD_TIMES:
        raise ValueError("unknown exact time for periods %s" % (periods,))
    return PERIOD_TIMES[periods[0]][0], PERIOD_TIMES[periods[-1]][1]


def expand_courses(
    courses: Iterable[CourseBlock],
    semester_id: str,
    semester_start: date,
    timezone: str,
) -> List[CalendarEvent]:
    if semester_start.isoweekday() != 1:
        raise ValueError("semesterStartDate must be a Monday")
    tz = ZoneInfo(timezone)
    events: List[CalendarEvent] = []
    for course in courses:
        start_time, end_time = resolve_period_times(course.periods)
        for week in course.weeks:
            day = semester_start + timedelta(days=(week - 1) * 7 + course.weekday - 1)
            start = datetime.combine(day, start_time, tzinfo=tz)
            end = datetime.combine(day, end_time, tzinfo=tz)
            identity = "%s|%s|%s|%s|%s" % (
                semester_id, course.source_id, week, course.weekday,
                "-".join(map(str, course.periods)),
            )
            uid = "%s@hnu-calendar.local" % uuid5(NAMESPACE_URL, identity).hex
            location = " ".join(part for part in (course.building, course.room) if part)
            description = "教师：%s\n周次：第%d周\n原始信息：%s" % (
                course.teacher or "未提供", week, course.raw,
            )
            events.append(CalendarEvent(
                uid=uid, source_id=course.source_id, semester_id=semester_id,
                week=week, weekday=course.weekday, name=course.name,
                teacher=course.teacher, start=start, end=end,
                location=location, description=description, raw=course.raw,
            ))
    return sorted(events, key=lambda item: (item.start, item.end, item.name, item.source_id))


def apply_adjustments(
    events: Iterable[CalendarEvent],
    adjustments: Iterable[Adjustment],
    semester_start: date,
    timezone: str,
) -> Tuple[List[CalendarEvent], List[str]]:
    result = list(events)
    warnings: List[str] = []
    tz = ZoneInfo(timezone)
    for change in adjustments:
        old_start, _ = resolve_period_times(change.original_periods)
        matched = [event for event in result if (
            event.name == change.course_name
            and (not change.teacher or event.teacher == change.teacher)
            and event.week in change.original_weeks
            and event.weekday == change.original_weekday
            and event.start.timetz().replace(tzinfo=None) == old_start
        )]
        if not matched:
            warnings.append("未找到调停课原事件：%s" % change.raw)
            continue
        if change.kind == "cancel":
            matched_uids = {event.uid for event in matched}
            result = [event for event in result if event.uid not in matched_uids]
            continue

        new_start, new_end = resolve_period_times(change.new_periods)
        replacements = []
        for index, event in enumerate(matched):
            if len(change.new_weeks) == len(change.original_weeks):
                old_index = change.original_weeks.index(event.week)
                new_week = change.new_weeks[old_index]
            else:
                new_week = change.new_weeks[min(index, len(change.new_weeks) - 1)]
            new_weekday = change.new_weekday or event.weekday
            day = semester_start + timedelta(days=(new_week - 1) * 7 + new_weekday - 1)
            replacements.append(replace(
                event, week=new_week, weekday=new_weekday,
                start=datetime.combine(day, new_start, tzinfo=tz),
                end=datetime.combine(day, new_end, tzinfo=tz),
                location=change.new_location or event.location,
                description=event.description + "\n调课信息：" + change.raw,
            ))
        replacement_by_uid = {event.uid: event for event in replacements}
        result = [replacement_by_uid.get(event.uid, event) for event in result]
    return sorted(result, key=lambda event: event.start), warnings
