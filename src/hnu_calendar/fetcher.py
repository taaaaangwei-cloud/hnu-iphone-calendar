from dataclasses import dataclass

from .authentication import BrowserSession, SessionExpired
from .config import AppConfig


class FetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class RawSchedule:
    timetable_html: str
    adjustments_html: str


class ScheduleFetcher:
    def __init__(self, config: AppConfig, session: BrowserSession):
        self.config = config
        self.session = session

    def fetch(self) -> RawSchedule:
        self.session.require_authenticated()
        try:
            self.session.page.goto(
                self.session.schedule_url,
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            time_mode = self.session.page.locator("#kbjcmsid").input_value(timeout=3_000)
        except Exception:
            time_mode = ""
        timetable = self._post(
            "/jsxsd/xskb/xskb_list.do",
            {
                "xnxq01id": self.config.semester_id,
                "zc": "", "sfFD": "on", "xstzd": "on",
                "wkbkc": "on", "xswk": "on",
                "kbjcmsid": time_mode,
            },
        )
        adjustments = self._post(
            "/jsxsd/xskb/loadTtkMxList",
            {"xnxqid": self.config.semester_id},
        )
        if 'id="timetable"' not in timetable:
            if "验证码" in timetable or 'type="password"' in timetable.lower():
                raise SessionExpired("获取课表时 Session 失效，请重新登录。")
            raise FetchError("学校返回的页面中没有课表，已保留上一份有效数据。")
        return RawSchedule(timetable, adjustments)

    def _post(self, path: str, form: dict) -> str:
        try:
            response = self.session.context.request.post(
                self.config.base_url + path,
                form=form, timeout=30_000,
            )
        except Exception as exc:
            raise FetchError("教务网络请求失败，已保留上一份有效数据：%s" % exc) from exc
        if not response.ok:
            raise FetchError("教务接口返回 HTTP %s，已保留上一份有效数据。" % response.status)
        return response.text()
