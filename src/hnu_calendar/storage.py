import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, List

from .models import CalendarEvent


def atomic_write_text(path: Path, text: str, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if private:
            os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_events(path: Path, events: Iterable[CalendarEvent]) -> None:
    payload = {"schemaVersion": 1, "events": [event.to_dict() for event in events]}
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", private=True)


def load_events(path: Path) -> List[CalendarEvent]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [CalendarEvent.from_dict(item) for item in payload.get("events", [])]

