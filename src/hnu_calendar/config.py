import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class AppConfig:
    semester_id: str
    semester_start_date: date
    timezone: str
    alert_times: List[int]
    calendar_name: str
    base_url: str
    profile_directory: Path
    data_directory: Path
    output_ics: Path
    max_weeks: int = 21
    sync_interval_minutes: int = 60

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        path = path.resolve()
        data = json.loads(path.read_text(encoding="utf-8"))
        root = path.parent

        def local_path(value: str) -> Path:
            candidate = Path(value).expanduser()
            return candidate if candidate.is_absolute() else root / candidate

        start = date.fromisoformat(data["semesterStartDate"])
        if start.isoweekday() != 1:
            raise ValueError("semesterStartDate 必须是教学第1周的星期一")
        timezone = data.get("timezone", "Asia/Shanghai")
        ZoneInfo(timezone)
        alerts = [int(value) for value in data.get("alertTimes", [30, 10])]
        if not alerts or any(value <= 0 for value in alerts):
            raise ValueError("alertTimes 必须是正整数分钟")
        return cls(
            semester_id=data["semesterId"], semester_start_date=start,
            timezone=timezone, alert_times=alerts,
            calendar_name=data.get("calendarName", "海南大学课程"),
            base_url=data.get("baseUrl", "https://jxgl.hainanu.edu.cn").rstrip("/"),
            profile_directory=local_path(data.get("profileDirectory", ".local/browser-profile")),
            data_directory=local_path(data.get("dataDirectory", ".local/data")),
            output_ics=local_path(data.get("outputIcs", "outputs/hnu-courses.ics")),
            max_weeks=int(data.get("maxWeeks", 21)),
            sync_interval_minutes=int(data.get("syncIntervalMinutes", 60)),
        )
