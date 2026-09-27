from dataclasses import dataclass, replace
from typing import Dict, Iterable, List, Sequence, Tuple

from .models import CalendarEvent


@dataclass(frozen=True)
class ReconcileResult:
    events: Tuple[CalendarEvent, ...]
    added: Tuple[str, ...]
    updated: Tuple[str, ...]
    deleted: Tuple[str, ...]


def _group_key(event: CalendarEvent) -> Tuple[str, str, int]:
    return event.semester_id, event.source_id, event.week


def reconcile(
    previous: Sequence[CalendarEvent],
    desired: Sequence[CalendarEvent],
    allow_empty: bool = True,
) -> ReconcileResult:
    if previous and not desired and not allow_empty:
        raise ValueError("empty timetable snapshot refused")

    old_groups: Dict[Tuple[str, str, int], List[CalendarEvent]] = {}
    for item in previous:
        old_groups.setdefault(_group_key(item), []).append(item)

    used = set()
    final: List[CalendarEvent] = []
    added: List[str] = []
    updated: List[str] = []
    for item in desired:
        candidates = [old for old in old_groups.get(_group_key(item), []) if old.uid not in used]
        if candidates:
            match = min(candidates, key=lambda old: abs((old.start - item.start).total_seconds()))
            used.add(match.uid)
            item = replace(item, uid=match.uid, sequence=match.sequence)
            if item.content_key() != match.content_key():
                item = replace(item, sequence=match.sequence + 1)
                updated.append(item.uid)
        else:
            added.append(item.uid)
        final.append(item)

    deleted = [item.uid for item in previous if item.uid not in used]
    return ReconcileResult(
        events=tuple(sorted(final, key=lambda event: event.start)),
        added=tuple(added), updated=tuple(updated), deleted=tuple(deleted),
    )
