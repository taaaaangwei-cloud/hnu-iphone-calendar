from datetime import date, datetime
import unittest

from hnu_calendar.models import CourseBlock
from hnu_calendar.semester import expand_courses


class SemesterTests(unittest.TestCase):
    def test_week_one_and_timezone_are_correct(self):
        course = CourseBlock("OFFER-1", "高等数学", "张老师", 2, (1, 3), (1, 2), "海甸", "5号教学楼", "302", "raw")
        events = expand_courses([course], "2026-2027-1", date(2026, 8, 31), "Asia/Shanghai")
        self.assertEqual(events[0].start, datetime.fromisoformat("2026-09-01T07:40:00+08:00"))
        self.assertEqual(events[0].end, datetime.fromisoformat("2026-09-01T09:20:00+08:00"))
        self.assertEqual(events[1].start.date(), date(2026, 9, 15))

    def test_course_ending_at_period_ten_does_not_run_to_period_eleven(self):
        course = CourseBlock("OFFER-1", "晚课", "张老师", 1, (1,), (9, 10), "海甸", "", "", "raw")
        event = expand_courses([course], "2026-2027-1", date(2026, 8, 31), "Asia/Shanghai")[0]
        self.assertEqual(event.start.strftime("%H:%M"), "19:20")
        self.assertEqual(event.end.strftime("%H:%M"), "21:00")


if __name__ == "__main__":
    unittest.main()

