"""Data models and timestamp normalization for the log indexing project."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from ipaddress import ip_address
from typing import Any


# Time complexity: O(1) for the fixed-format timestamp strings used by the application.
def normalize_timestamp(value: str) -> str:
    """Normalize an ISO-like timestamp to ``YYYY-MM-DD HH:MM:SS``.

    Date-only values are accepted and treated as midnight. Time-zone-aware
    values are converted to UTC before the timezone information is removed.
    """
    raw = str(value).strip()
    if not raw:
        raise ValueError("timestamp is required")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {raw!r}; use YYYY-MM-DD HH:MM:SS") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


@dataclass(frozen=True)
class LogRecord:
    """One event captured by a computer, server, or network service."""

    event_id: int
    timestamp: str
    source_ip: str
    severity: str
    event: str

    # Time complexity: O(1) for fixed-length fields: normalize the timestamp and validate a single source IP.
    def __post_init__(self) -> None:
        if not isinstance(self.event_id, int) or self.event_id < 0:
            raise ValueError("event_id must be a non-negative integer")
        object.__setattr__(self, "timestamp", normalize_timestamp(self.timestamp))

        # Validate source IPs rather than merely checking that the field is non-empty.
        raw_ip = "" if self.source_ip is None else str(self.source_ip).strip()
        if not raw_ip:
            raise ValueError("source_ip is required")
        try:
            normalized_ip = str(ip_address(raw_ip))
        except ValueError as exc:
            raise ValueError("source_ip must be a valid IPv4 or IPv6 address") from exc

        severity = "" if self.severity is None else str(self.severity).strip()
        event = "" if self.event is None else str(self.event).strip()
        if not severity:
            raise ValueError("severity is required")
        if not event:
            raise ValueError("event description is required")
        object.__setattr__(self, "source_ip", normalized_ip)
        object.__setattr__(self, "severity", severity.upper())
        object.__setattr__(self, "event", event)

    # Time complexity: O(c): normalize c CSV columns; c is fixed for the project schema.
    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "LogRecord":
        """Create a validated record from CSV-style field names."""
        normalized = {str(key).strip().lower(): value for key, value in row.items() if key is not None}
        # Allow a common alternative heading for the event description.
        event_value = normalized.get("event", normalized.get("event_description", ""))
        try:
            event_id = int(str(normalized.get("event_id", "")).strip())
        except (TypeError, ValueError) as exc:
            raise ValueError("event_id must be an integer") from exc
        return cls(
            event_id=event_id,
            timestamp=str(normalized.get("timestamp", "")),
            source_ip=str(normalized.get("source_ip", "")),
            severity=str(normalized.get("severity", "")),
            event=str(event_value),
        )

    # Time complexity: O(1): return the fixed five-field record representation.
    def to_row(self) -> dict[str, str | int]:
        """Return fields in the project's CSV column order."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "source_ip": self.source_ip,
            "severity": self.severity,
            "event": self.event,
        }


@dataclass
class LoadReport:
    """Summary returned after loading a CSV file."""

    total_rows: int = 0
    loaded_rows: int = 0
    duplicate_ids: int = 0
    invalid_rows: int = 0
    issues: list[str] = field(default_factory=list)

    # Time complexity: O(1): format four counters and a fixed-size summary.
    def summary(self) -> str:
        """Return a concise, predictable summary for the GUI and tests."""
        return (
            f"Rows read: {self.total_rows}\n"
            f"Records loaded: {self.loaded_rows}\n"
            f"Duplicate IDs skipped: {self.duplicate_ids}\n"
            f"Invalid rows skipped: {self.invalid_rows}"
        )
