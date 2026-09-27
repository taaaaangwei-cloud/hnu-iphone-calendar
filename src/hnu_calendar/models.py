from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class CourseBlock:
    source_id: str
    name: str
    teacher: str
    weekday: int
    weeks: Tuple[int, ...]
    periods: Tuple[int, ...]
    campus: str
    building: str
    room: str
    raw: str


@dataclass(frozen=True)
class CalendarEvent:
    uid: str
    source_id: str
    semester_id: str
    week: int
    weekday: int
    name: str
    teacher: str
    start: datetime
    end: datetime
    location: str
    description: str
    raw: str
    sequence: int = 0

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["start"] = self.start.isoformat()
        data["end"] = self.end.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalendarEvent":
        values = dict(data)
        values["start"] = datetime.fromisoformat(values["start"])
        values["end"] = datetime.fromisoformat(values["end"])
        return cls(**values)

    def content_key(self) -> Tuple[Any, ...]:
        return (
            self.name, self.teacher, self.start, self.end,
            self.location, self.description, self.raw,
        )


@dataclass(frozen=True)
class Adjustment:
    kind: str
    course_name: str
    teacher: str
    original_weeks: Tuple[int, ...]
    original_weekday: int
    original_periods: Tuple[int, ...]
    new_weeks: Tuple[int, ...]
    new_weekday: Optional[int]
    new_periods: Tuple[int, ...]
    new_location: str
    status: str
    raw: str
