import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

from .automation import install as install_automation
from .authentication import BrowserSession, SessionExpired
from .calendar import render_ics
from .config import AppConfig
from .fetcher import FetchError, ScheduleFetcher
from .icloud import ICloudSyncError, sync_to_icloud
from .parser import ParseError, TimetableParser, parse_adjustments
from .semester import apply_adjustments, expand_courses
from .storage import atomic_write_text, load_events, save_events
from .sync import reconcile


def _config(path: str) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError("找不到 config.json，请先运行 `cp config.example.json config.json`")
    return AppConfig.load(config_path)


def login(config: AppConfig) -> None:
    with BrowserSession(config, headless=False) as session:
        session.interactive_login()
    print("登录状态已安全保存在本机浏览器配置中。")


def sync(config: AppConfig, ics_only: bool) -> None:
    state_path = config.data_directory / "events.json"
    previous = load_events(state_path)

    def status(stage: str, detail: str = "") -> None:
        atomic_write_text(
            config.data_directory / "sync-status.json",
            json.dumps({
                "stage": stage,
                "detail": detail,
                "time": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False, indent=2),
            private=True,
        )

    try:
        status("starting_browser", "正在启动专用 Chrome")
        with BrowserSession(config, headless=True) as session:
            status("fetching", "正在读取学校课表接口")
            raw = ScheduleFetcher(config, session).fetch()
            status("fetched", "学校课表读取完成")
        status("browser_closed", "专用 Chrome 已关闭")

        courses = TimetableParser(config.max_weeks).parse(raw.timetable_html)
        if not courses:
            atomic_write_text(
                config.data_directory / "last-failed-timetable.html",
                raw.timetable_html,
                private=True,
            )
            raise ParseError("学校返回空课表；为防止误删，已中止同步并保留旧数据。")
        desired = expand_courses(
            courses, config.semester_id, config.semester_start_date, config.timezone,
        )
        changes = parse_adjustments(raw.adjustments_html, config.max_weeks)
        desired, warnings = apply_adjustments(
            desired, changes, config.semester_start_date, config.timezone,
        )
        result = reconcile(previous, desired, allow_empty=False)
        ics = render_ics(result.events, config.calendar_name, config.timezone, config.alert_times)

        # Only valid snapshots reach disk or Calendar. A fetch/parse failure changes nothing.
        atomic_write_text(config.output_ics, ics)
        atomic_write_text(config.data_directory / "last-good-timetable.html", raw.timetable_html, private=True)
        atomic_write_text(config.data_directory / "last-good-adjustments.html", raw.adjustments_html, private=True)

        cloud = None
        if not ics_only:
            status("writing_calendar", "正在更新 iCloud 日历")
            cloud = sync_to_icloud(
                result.events, config.calendar_name, config.alert_times, config.data_directory,
            )
        save_events(state_path, result.events)
        status("complete", "同步完成")
        print(json.dumps({
            "events": len(result.events), "added": len(result.added),
            "updated": len(result.updated), "deleted": len(result.deleted),
            "ics": str(config.output_ics), "iCloud": cloud,
            "warnings": warnings,
        }, ensure_ascii=False, indent=2))
    except Exception as exc:
        status("failed", str(exc))
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="海南大学课表同步到 iPhone 日历")
    parser.add_argument("--config", default="config.json")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("login", help="手动登录并保存合法 Session")
    sync_parser = commands.add_parser("sync", help="获取、生成 ICS 并同步 iCloud")
    sync_parser.add_argument("--ics-only", action="store_true", help="只生成 ICS，不修改日历")
    commands.add_parser("install-automation", help="安装每小时自动同步")
    args = parser.parse_args(argv)
    try:
        config = _config(args.config)
        if args.command == "login":
            login(config)
        elif args.command == "sync":
            sync(config, args.ics_only)
        else:
            path = install_automation(config, Path(args.config))
            print("自动同步已安装：%s" % path)
        return 0
    except (FileNotFoundError, RuntimeError, ValueError, SessionExpired, FetchError, ParseError, ICloudSyncError) as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
