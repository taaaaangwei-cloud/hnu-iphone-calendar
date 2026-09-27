from datetime import datetime
from zoneinfo import ZoneInfo
import unittest

from hnu_calendar.models import CalendarEvent
from hnu_calendar.sync import reconcile


def event(uid, source, start, room="302"):
    tz = ZoneInfo("Asia/Shanghai")
    dt = datetime.fromisoformat(start).replace(tzinfo=tz)
    return CalendarEvent(uid, source, "2026-2027-1", 1, dt.isoweekday(), "高等数学", "张老师", dt, dt.replace(hour=dt.hour + 1), room, "", "")


class SyncTests(unittest.TestCase):
    def test_reuses_uid_for_time_and_room_changes_and_detects_delete(self):
        old = [event("old-uid@hnu-calendar.local", "OFFER-1", "2026-09-01T07:40:00")]
        changed = [event("", "OFFER-1", "2026-09-01T09:45:00", "414")]
        result = reconcile(old, changed)
        self.assertEqual(result.events[0].uid, old[0].uid)
        self.assertEqual(result.events[0].sequence, 1)
        self.assertEqual(result.updated, (old[0].uid,))
        self.assertEqual(result.deleted, ())
        removed = reconcile(result.events, [])
        self.assertEqual(removed.deleted, (old[0].uid,))

    def test_second_identical_sync_is_a_noop(self):
        old = [event("old-uid@hnu-calendar.local", "OFFER-1", "2026-09-01T07:40:00")]
        desired = [event("new-generated-uid@hnu-calendar.local", "OFFER-1", "2026-09-01T07:40:00")]
        result = reconcile(old, desired)
        self.assertEqual(result.events[0].uid, old[0].uid)
        self.assertEqual(result.events[0].sequence, 0)
        self.assertEqual((result.added, result.updated, result.deleted), ((), (), ()))

    def test_rejects_empty_snapshot_before_destructive_sync(self):
        old = [event("old-uid@hnu-calendar.local", "OFFER-1", "2026-09-01T07:40:00")]
        with self.assertRaisesRegex(ValueError, "empty"):
            reconcile(old, [], allow_empty=False)


if __name__ == "__main__":
    unittest.main()
