from pathlib import Path
import unittest

from hnu_calendar.parser import TimetableParser, parse_weeks


FIXTURE = Path(__file__).parent / "fixtures" / "timetable.html"


class ParserTests(unittest.TestCase):
    def test_reads_semantic_course_fields_and_multiple_courses_in_one_cell(self):
        courses = TimetableParser(max_weeks=18).parse(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual([c.name for c in courses], ["高等数学", "大学英语", "化学实验"])
        self.assertEqual(courses[0].weeks, (1, 2, 4))
        self.assertEqual(courses[0].periods, (1, 2))
        self.assertEqual(courses[0].weekday, 2)
        self.assertEqual(courses[0].building, "海甸5号教学楼")
        self.assertEqual(courses[0].room, "(海甸)5-302")
        self.assertEqual(courses[0].source_id, "OFFER-001")
        self.assertEqual(courses[2].weeks, tuple(range(2, 19, 2)))

    def test_reads_detailed_course_layer_hidden_in_raw_server_html(self):
        html = FIXTURE.read_text(encoding="utf-8").replace(
            'class="kbcontent" style="position:relative"',
            'class="kbcontent" style="display: none; position: relative"',
        )

        courses = TimetableParser(max_weeks=18).parse(html)

        self.assertEqual([course.name for course in courses], ["高等数学", "大学英语", "化学实验"])

    def test_week_parser_supports_lists_ranges_and_odd_even(self):
        self.assertEqual(parse_weeks("4-5,7-10,12-18(周)", 18), (4, 5, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18))
        self.assertEqual(parse_weeks("单周", 6), (1, 3, 5))
        self.assertEqual(parse_weeks("双周", 6), (2, 4, 6))


if __name__ == "__main__":
    unittest.main()
