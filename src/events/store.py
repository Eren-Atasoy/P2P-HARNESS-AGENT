"""Append-only, single-writer EventStore corresponding to .p2p/events.jsonl."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

from src.models.enums import EventType
from src.models.event import Event
from src.events.lock import file_lock


class EventStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.lock_path = self.path.parent / (self.path.name + ".lock")

    def _ensure_dir(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def last_seq(self) -> int:
        if not self.path.exists():
            return 0
        last = 0
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    seq = data.get("seq", 0)
                    if seq > last:
                        last = seq
                except Exception:
                    continue
        return last

    def append(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        task_id: Optional[str] = None,
        run_id: Optional[str] = None,
        ts: Optional[datetime] = None,
    ) -> Event:
        """Appends a new event with guaranteed monotonic seq and file locking."""
        self._ensure_dir()
        with file_lock(self.lock_path):
            current_seq = self.last_seq()
            new_seq = current_seq + 1
            timestamp = ts or datetime.now(timezone.utc)

            event = Event(
                seq=new_seq,
                ts=timestamp,
                type=event_type,
                task_id=task_id,
                run_id=run_id,
                payload=payload,
            )

            # JSON string with ISO-8601 formatting for ts
            line = event.model_dump_json()
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()

            return event

    def append_event(self, event: Event) -> Event:
        """Appends an existing Event model, enforcing sequence monotonicity under lock."""
        self._ensure_dir()
        with file_lock(self.lock_path):
            current_seq = self.last_seq()
            # If event seq is not current_seq + 1, set it
            if event.seq != current_seq + 1:
                event = event.model_copy(update={"seq": current_seq + 1})

            line = event.model_dump_json()
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()

            return event

    def read_all(self) -> list[Event]:
        """Reads and validates all events from the event log."""
        if not self.path.exists():
            return []
        events: list[Event] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    events.append(Event.model_validate(data))
                except Exception as e:
                    # In production we log warning; corrupted line shouldn't crash reading previous valid events
                    continue
        return events
