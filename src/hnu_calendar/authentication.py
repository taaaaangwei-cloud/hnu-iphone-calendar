import json
from pathlib import Path
import time
from typing import Optional

from .config import AppConfig


class SessionExpired(RuntimeError):
    pass


class BrowserSession:
    """A legal, user-created school session in an isolated local Chrome profile."""

    def __init__(self, config: AppConfig, headless: bool):
        self.config = config
        self.headless = headless
        self._playwright = None
        self.context = None
        self.page = None

    def __enter__(self) -> "BrowserSession":
        from playwright.sync_api import sync_playwright

        self.config.profile_directory.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        try:
            self.context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.config.profile_directory),
                channel="chrome", headless=self.headless, timeout=30_000,
            )
            self.context.set_default_timeout(30_000)
            self.context.set_default_navigation_timeout(30_000)
            if self.storage_state_path.exists():
                state = json.loads(self.storage_state_path.read_text(encoding="utf-8"))
                if state.get("cookies"):
                    self.context.add_cookies(state["cookies"])
        except Exception as exc:
            self._playwright.stop()
            self._playwright = None
            raise RuntimeError(
                "无法启动专用 Chrome。请关闭残留的课表登录窗口后重试；"
                "若正在 Codex 沙箱内运行，请从 Finder 双击 login.command。"
            ) from exc
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.context:
            self.context.close()
        if self._playwright:
            self._playwright.stop()

    @property
    def schedule_url(self) -> str:
        return self.config.base_url + "/jsxsd/xskb/xskb_list.do"

    @property
    def storage_state_path(self) -> Path:
        return self.config.profile_directory / "storage-state.json"

    def save_storage_state(self) -> None:
        self.storage_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.context.storage_state(path=str(self.storage_state_path))
        self.storage_state_path.chmod(0o600)

    def is_authenticated(self) -> bool:
        try:
            response = self.context.request.get(self.schedule_url, timeout=10_000)
            html = response.text()
            return bool(response.ok and 'id="timetable"' in html)
        except Exception:
            return False

    def require_authenticated(self) -> None:
        if not self.is_authenticated():
            raise SessionExpired(
                "教务 Session 已失效。请先运行 `.venv/bin/hnu-calendar login`，"
                "在打开的 Chrome 中手动登录并输入验证码。"
            )

    def interactive_login(
        self, timeout_seconds: float = 600, poll_interval_seconds: float = 3,
    ) -> None:
        self.page.goto(self.config.base_url + "/jsxsd/", wait_until="domcontentloaded")
        print("\n请在打开的 Chrome 窗口中完成学校登录和验证码。")
        print("检测到登录成功后会自动继续，无需回终端按 Enter。\n")
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self.is_authenticated():
                self.save_storage_state()
                print("已检测到有效登录。")
                return
            time.sleep(poll_interval_seconds)
        raise SessionExpired("等待登录超过 10 分钟，请重新运行登录程序。")
