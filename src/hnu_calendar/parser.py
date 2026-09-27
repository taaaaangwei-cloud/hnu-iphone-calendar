import hashlib
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag

from .models import Adjustment, CourseBlock


class ParseError(ValueError):
    pass


def parse_weeks(value: str, max_weeks: int) -> Tuple[int, ...]:
    text = value.replace("（", "(").replace("）", ")").replace("，", ",").strip()
    text = re.sub(r"\(周\)", "", text).strip()
    if "单周" in text:
        return tuple(range(1, max_weeks + 1, 2))
    if "双周" in text:
        return tuple(range(2, max_weeks + 1, 2))

    weeks = set()
    for part in filter(None, (item.strip() for item in text.split(","))):
        match = re.fullmatch(r"(\d+)\s*[-~至]\s*(\d+)", part)
        if match:
            start, end = map(int, match.groups())
            if start > end:
                raise ParseError("invalid descending week range: %s" % part)
            weeks.update(range(start, end + 1))
        elif part.isdigit():
            weeks.add(int(part))
        else:
            raise ParseError("unknown week expression: %s" % value)
    result = tuple(sorted(week for week in weeks if 1 <= week <= max_weeks))
    if not result:
        raise ParseError("empty week expression: %s" % value)
    return result


def parse_periods(value: str) -> Tuple[int, ...]:
    match = re.search(r"[\[【]([^\]】]+?)节[\]】]", value)
    if not match:
        raise ParseError("missing periods: %s" % value)
    numbers = tuple(int(item) for item in re.findall(r"\d+", match.group(1)))
    if not numbers or any(period < 1 or period > 15 for period in numbers):
        raise ParseError("invalid periods: %s" % value)
    return numbers


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _source_from_font(font: Tag) -> Optional[str]:
    image = font.find_previous("img")
    if image and image.get("src"):
        values = parse_qs(urlparse(image["src"]).query).get("id")
        if values:
            return values[0]
    return None


class TimetableParser:
    def __init__(self, max_weeks: int = 30):
        self.max_weeks = max_weeks

    def parse(self, html: str) -> List[CourseBlock]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", id="timetable")
        if table is None:
            if self._looks_like_login(html):
                raise ParseError("login session expired")
            raise ParseError("timetable table not found")

        courses: List[CourseBlock] = []
        rows = table.find_all("tr")
        for row in rows[1:]:
            cells = row.find_all(["td", "th"], recursive=False)
            for weekday, cell in enumerate(cells[1:8], start=1):
                for block in self._detailed_course_blocks(cell):
                    courses.extend(self._parse_block(block, weekday))

        unique: Dict[Tuple[object, ...], CourseBlock] = {}
        for course in courses:
            key = (
                course.source_id, course.weekday, course.weeks,
                course.periods, course.name, course.room,
            )
            unique[key] = course
        return list(unique.values())

    @staticmethod
    def _detailed_course_blocks(cell: Tag) -> List[Tag]:
        # The raw timetable response keeps every detailed ``kbcontent`` layer
        # hidden; page JavaScript chooses which layer to show afterwards.
        # A schedule field identifies the populated detailed layer reliably,
        # while excluding the empty alternate layers returned beside it.
        return [
            div
            for div in cell.find_all("div", class_="kbcontent", recursive=False)
            if div.find("font", title="周次(节次)") is not None
        ]

    def _parse_block(self, block: Tag, weekday: int) -> List[CourseBlock]:
        records: List[CourseBlock] = []
        current: Optional[Dict[str, str]] = None
        for font in block.find_all("font"):
            value = _clean(font.get_text(" ", strip=True))
            title = font.get("title")
            name = font.get("name")
            if value and not title and not name:
                if current:
                    records.append(self._finish(current, weekday))
                current = {"course": value, "source": _source_from_font(font) or ""}
                continue
            if current is None:
                continue
            if title == "教师":
                current["teacher"] = value
            elif title == "周次(节次)":
                current["schedule"] = value
            elif title == "教学楼":
                current["building"] = value.strip("【】[]")
            elif title == "教室":
                current["room"] = value
            elif title == "通知单编号":
                current["source"] = re.sub(r"^.*?[：:]", "", value).strip()
        if current:
            records.append(self._finish(current, weekday))
        return records

    def _finish(self, values: Dict[str, str], weekday: int) -> CourseBlock:
        schedule = values.get("schedule", "")
        if not schedule:
            raise ParseError("course has no week/period data: %s" % values.get("course", ""))
        weeks_text = re.sub(r"[\[【].*$", "", schedule)
        weeks = parse_weeks(weeks_text, self.max_weeks)
        periods = parse_periods(schedule)
        room = values.get("room", "")
        campus_match = re.match(r"^[\(（]([^\)）]+)[\)）]", room)
        campus = campus_match.group(1) if campus_match else ""
        source = values.get("source") or hashlib.sha256(
            (values.get("course", "") + values.get("teacher", "") + schedule + str(weekday)).encode("utf-8")
        ).hexdigest()[:20]
        raw = " | ".join(filter(None, [values.get("course"), values.get("teacher"), schedule, values.get("building"), room]))
        return CourseBlock(
            source_id=source,
            name=values.get("course", ""),
            teacher=values.get("teacher", ""),
            weekday=weekday,
            weeks=weeks,
            periods=periods,
            campus=campus,
            building=values.get("building", ""),
            room=room,
            raw=raw,
        )

    @staticmethod
    def _looks_like_login(html: str) -> bool:
        lower = html.lower()
        return "captcha" in lower or "验证码" in html or ('type="password"' in lower)


_WEEKDAYS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "天": 7}


def _parse_slot(value: str) -> Tuple[int, Tuple[int, ...]]:
    weekday = re.search(r"(?:星期|周)([一二三四五六日天])", value)
    if not weekday:
        raise ParseError("unknown weekday in adjustment: %s" % value)
    return _WEEKDAYS[weekday.group(1)], parse_periods(value)


def parse_adjustments(html: str, max_weeks: int = 30) -> List[Adjustment]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="dataTables") or soup.find("table")
    if table is None:
        return []
    rows = table.find_all("tr")
    if not rows:
        return []
    headers = [_clean(cell.get_text(" ", strip=True)) for cell in rows[0].find_all(["th", "td"])]
    result: List[Adjustment] = []
    for row in rows[1:]:
        values = [_clean(cell.get_text(" ", strip=True)) for cell in row.find_all("td")]
        if not values:
            continue
        record = dict(zip(headers, values))
        status = record.get("状态", "")
        if any(word in status for word in ("撤销", "作废", "不通过", "拒绝")):
            continue
        kind_text = record.get("调课类型", "")
        kind = "cancel" if "停" in kind_text else "move" if "调" in kind_text else ""
        if not kind:
            continue
        try:
            old_day, old_periods = _parse_slot(record.get("调前时间", ""))
            original_weeks = parse_weeks(record.get("调整周次") or record.get("上课周次", ""), max_weeks)
            if kind == "move":
                new_day, new_periods = _parse_slot(record.get("调后时间", ""))
                new_weeks = parse_weeks(record.get("调后周次") or record.get("调整周次", ""), max_weeks)
            else:
                new_day, new_periods, new_weeks = None, (), ()
        except ParseError:
            continue
        result.append(Adjustment(
            kind=kind, course_name=record.get("课程名称", ""),
            teacher=record.get("上课教师", ""), original_weeks=original_weeks,
            original_weekday=old_day, original_periods=old_periods,
            new_weeks=new_weeks, new_weekday=new_day, new_periods=new_periods,
            new_location=record.get("调后地点", ""), status=status,
            raw=" | ".join(values),
        ))
    return result
