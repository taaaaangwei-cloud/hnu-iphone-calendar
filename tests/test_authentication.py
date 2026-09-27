from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from hnu_calendar.authentication import BrowserSession


class AuthenticationTests(unittest.TestCase):
    def test_interactive_login_saves_session_with_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            config = SimpleNamespace(
                base_url="https://school.example",
                profile_directory=Path(directory) / "browser-profile",
            )
            session = BrowserSession(config, headless=False)
            session.page = Mock()
            session.is_authenticated = Mock(return_value=True)
            session.context = Mock()

            def write_state(path):
                Path(path).write_text('{"cookies": []}', encoding="utf-8")

            session.context.storage_state.side_effect = write_state
            with patch("time.sleep"):
                session.interactive_login()

            state_path = config.profile_directory / "storage-state.json"
            session.context.storage_state.assert_called_once_with(path=str(state_path))
            self.assertEqual(state_path.stat().st_mode & 0o777, 0o600)

    def test_authentication_probe_does_not_navigate_the_login_page(self):
        session = BrowserSession(SimpleNamespace(base_url="https://school.example"), headless=False)
        session.page = Mock()
        response = Mock(ok=True)
        response.text.return_value = '<table id="timetable"></table>'
        request = Mock()
        request.get.return_value = response
        session.context = SimpleNamespace(request=request)

        self.assertTrue(session.is_authenticated())
        request.get.assert_called_once_with(
            "https://school.example/jsxsd/xskb/xskb_list.do", timeout=10_000,
        )
        session.page.goto.assert_not_called()

    def test_interactive_login_finishes_when_session_becomes_valid_without_stdin(self):
        session = BrowserSession(SimpleNamespace(base_url="https://school.example"), headless=False)
        session.page = Mock()
        session.is_authenticated = Mock(side_effect=[False, True])
        session.save_storage_state = Mock()

        with patch("builtins.input", side_effect=AssertionError("不应读取终端输入")), \
             patch("time.sleep"):
            session.interactive_login()

        self.assertEqual(session.is_authenticated.call_count, 2)


if __name__ == "__main__":
    unittest.main()
