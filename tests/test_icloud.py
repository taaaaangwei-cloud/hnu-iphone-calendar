from pathlib import Path
import plistlib
import unittest


class ICloudSyncTests(unittest.TestCase):
    def test_eventkit_syncer_declares_full_calendar_access(self):
        root = Path(__file__).resolve().parents[1]
        info_path = root / "macos" / "HNUCalendarSync-Info.plist"

        with info_path.open("rb") as handle:
            info = plistlib.load(handle)

        self.assertEqual(info["CFBundleIdentifier"], "local.hnu.course-calendar.sync")
        self.assertTrue(info["NSCalendarsFullAccessUsageDescription"])


if __name__ == "__main__":
    unittest.main()
