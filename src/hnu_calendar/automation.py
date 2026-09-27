import os
import plistlib
import subprocess
from pathlib import Path

from .config import AppConfig


LABEL = "local.hnu.course-calendar"


def install(config: AppConfig, config_path: Path) -> Path:
    root = Path(__file__).resolve().parents[2]
    executable = root / ".venv" / "bin" / "hnu-calendar"
    if not executable.exists():
        raise RuntimeError("找不到虚拟环境，请先运行 setup.command")
    logs = config.data_directory / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    plist_path = Path.home() / "Library" / "LaunchAgents" / (LABEL + ".plist")
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": LABEL,
        "ProgramArguments": [str(executable), "--config", str(config_path.resolve()), "sync"],
        "WorkingDirectory": str(root),
        "RunAtLoad": True,
        "StartInterval": max(15, config.sync_interval_minutes) * 60,
        "StandardOutPath": str(logs / "sync.log"),
        "StandardErrorPath": str(logs / "sync-error.log"),
    }
    with plist_path.open("wb") as handle:
        plistlib.dump(payload, handle)
    domain = "gui/%d" % os.getuid()
    subprocess.run(["launchctl", "bootout", domain + "/" + LABEL], capture_output=True)
    result = subprocess.run(["launchctl", "bootstrap", domain, str(plist_path)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("安装自动同步失败：%s" % result.stderr.strip())
    return plist_path

