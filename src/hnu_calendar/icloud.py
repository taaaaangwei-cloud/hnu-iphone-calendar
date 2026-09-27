import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from .models import CalendarEvent
from .storage import atomic_write_text


class ICloudSyncError(RuntimeError):
    pass


def sync_to_icloud(
    events: Iterable[CalendarEvent],
    calendar_name: str,
    alert_times: Iterable[int],
    data_directory: Path,
) -> dict:
    root = Path(__file__).resolve().parents[2]
    source = root / "macos" / "EventKitSync.swift"
    info_source = root / "macos" / "HNUCalendarSync-Info.plist"
    app = data_directory / "bin" / "HNUCalendarSync.app"
    contents = app / "Contents"
    binary = contents / "MacOS" / "HNUCalendarSync"
    info_target = contents / "Info.plist"
    newest_source = max(source.stat().st_mtime, info_source.stat().st_mtime)
    if not binary.exists() or binary.stat().st_mtime < newest_source:
        cache = data_directory / "swift-module-cache"
        cache.mkdir(parents=True, exist_ok=True)
        binary.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(info_source, info_target)
        environment = dict(os.environ)
        environment["CLANG_MODULE_CACHE_PATH"] = str(cache)
        environment["SWIFT_MODULECACHE_PATH"] = str(cache)
        result = subprocess.run(
            [
                "swiftc", str(source), "-o", str(binary),
                "-framework", "EventKit", "-framework", "AppKit",
            ],
            capture_output=True, text=True, env=environment,
        )
        if result.returncode:
            raise ICloudSyncError("EventKit 同步器编译失败：%s" % result.stderr.strip())
        result = subprocess.run(
            [
                "codesign", "--force", "--deep", "--sign", "-",
                "--identifier", "local.hnu.course-calendar.sync", str(app),
            ],
            capture_output=True, text=True,
        )
        if result.returncode:
            raise ICloudSyncError("EventKit 同步器签名失败：%s" % result.stderr.strip())

    values = list(events)
    if not values:
        raise ICloudSyncError("拒绝把空快照写入 iCloud 日历")
    payload = {
        "calendarName": calendar_name,
        "rangeStart": min(event.start for event in values).isoformat(),
        "rangeEnd": max(event.end for event in values).isoformat(),
        "alertTimes": list(alert_times),
        "events": [event.to_dict() for event in values],
    }
    input_path = data_directory / "eventkit-input.json"
    atomic_write_text(input_path, json.dumps(payload, ensure_ascii=False), private=True)
    result = subprocess.run([str(binary), str(input_path)], capture_output=True, text=True)
    if result.returncode:
        raise ICloudSyncError(result.stderr.strip() or "写入 iCloud 日历失败")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ICloudSyncError("EventKit 返回了无法识别的结果") from exc
