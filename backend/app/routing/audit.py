from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    actor_id: str | None
    timestamp: str
    details: dict[str, Any]

    @classmethod
    def create(cls, event_type: str, actor_id: str | None, details: dict[str, Any] | None = None):
        return cls(event_type, actor_id, datetime.now(timezone.utc).isoformat(), details or {})
