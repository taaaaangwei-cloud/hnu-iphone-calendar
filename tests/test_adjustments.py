from datetime import date
from pathlib import Path
import unittest

from hnu_calendar.models import CourseBlock
from hnu_calendar.parser import parse_adjustments
from hnu_calendar.semester import apply_adjustments, expand_courses


FIXTURE = Path(__file__).parent / "fixtures" / "adjustments.html"


class AdjustmentTests(unittest.TestCase):
    def test_move_keeps_uid_and_cancel_removes_original_event(self):
        courses = [
            CourseBlock("MATH-OFFER", "高等数学", "张老师", 2, (3,), (1, 2), "海甸", "5号教学楼", "5-302", "raw"),
            CourseBlock("ENG-OFFER", "大学英语", "李老师", 4, (4,), (1, 2), "海甸", "3号教学楼", "3-204", "raw"),
        ]
        original = expand_courses(courses, "2026-2027-1", date(2026, 8, 31), "Asia/Shanghai")
        math_uid = original[0].uid
        changes = parse_adjustments(FIXTURE.read_text(encoding="utf-8"))
        result, warnings = apply_adjustments(original, changes, date(2026, 8, 31), "Asia/Shanghai")
        self.assertEqual(warnings, [])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].uid, math_uid)
        self.assertEqual(result[0].start.isoformat(), "2026-09-16T09:45:00+08:00")
        self.assertEqual(result[0].end.isoformat(), "2026-09-16T11:25:00+08:00")
        self.assertEqual(result[0].location, "5-414")

    def test_rejected_adjustment_is_ignored(self):
        html = FIXTURE.read_text(encoding="utf-8").replace("已通过", "已撤销")
        self.assertEqual(parse_adjustments(html), [])


if __name__ == "__main__":
    unittest.main()
