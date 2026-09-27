from datetime import datetime
from zoneinfo import ZoneInfo
import unittest

from hnu_calendar.calendar import render_ics
from hnu_calendar.models import CalendarEvent


class CalendarTests(unittest.TestCase):
    def test_renders_utf8_timezone_stable_uid_and_two_alarms(self):
        tz = ZoneInfo("Asia/Shanghai")
        event = CalendarEvent(
            uid="stable-uid@hnu-calendar.local",
            source_id="OFFER-1", semester_id="2026-2027-1", week=1, weekday=2,
            name="高等数学", teacher="张老师", start=datetime(2026, 9, 1, 7, 40, tzinfo=tz),
            end=datetime(2026, 9, 1, 9, 20, tzinfo=tz), location="5号教学楼 302",
            description="教师：张老师\n周次：第1周\n原始信息：测试", raw="测试",
        )
        text = render_ics([event], "海南大学课程", "Asia/Shanghai", [30, 10], now=datetime(2026, 8, 1, tzinfo=ZoneInfo("UTC")))
        self.assertTrue(text.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertIn("UID:stable-uid@hnu-calendar.local", text)
        self.assertIn("DTSTART;TZID=Asia/Shanghai:20260901T074000", text)
        self.assertIn("SUMMARY:高等数学", text)
        self.assertEqual(text.count("BEGIN:VALARM"), 2)
        self.assertIn("TRIGGER:-PT30M", text)
        self.assertIn("TRIGGER:-PT10M", text)
        self.assertNotIn("RRULE", text)
        self.assertTrue(text.endswith("END:VCALENDAR\r\n"))
        self.assertLessEqual(max(len(line.encode("utf-8")) for line in text.split("\r\n")), 75)


if __name__ == "__main__":
    unittest.main()
