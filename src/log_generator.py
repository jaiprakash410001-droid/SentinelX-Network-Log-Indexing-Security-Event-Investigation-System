"""Create reproducible synthetic log datasets spanning the previous five years."""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

CSV_FIELDS = ["event_id", "timestamp", "source_ip", "severity", "event"]

# 30 distinct event descriptions across informational, warning, security, and error cases.
# The weight controls how often an event appears in the synthetic dataset.
EVENT_TEMPLATES: list[tuple[str, str, int]] = [
    ("INFO", "Successful login", 14),
    ("INFO", "Successful logout", 7),
    ("INFO", "Connection accepted", 10),
    ("INFO", "Connection closed", 7),
    ("INFO", "VPN connection established", 4),
    ("INFO", "DNS query resolved", 8),
    ("INFO", "File access granted", 7),
    ("INFO", "Configuration file accessed", 3),
    ("INFO", "Service started", 3),
    ("INFO", "Backup completed", 2),
    ("INFO", "Software update installed", 2),
    ("INFO", "New device connected", 3),
    ("INFO", "User session expired", 4),
    ("MEDIUM", "Access denied", 8),
    ("MEDIUM", "Connection rejected", 5),
    ("MEDIUM", "Unusual request rate detected", 4),
    ("MEDIUM", "Password reset requested", 3),
    ("MEDIUM", "Firewall rule matched", 4),
    ("MEDIUM", "Certificate expires soon", 1),
    ("MEDIUM", "Disk usage above threshold", 2),
    ("HIGH", "Failed login attempt", 10),
    ("HIGH", "Multiple failed login attempts", 4),
    ("HIGH", "Privilege escalation request denied", 3),
    ("HIGH", "Suspicious IP blocked", 3),
    ("HIGH", "Unexpected admin access detected", 2),
    ("HIGH", "Malware signature detected", 1),
    ("ERROR", "Application exception recorded", 4),
    ("ERROR", "Service connection timeout", 4),
    ("ERROR", "Disk write operation failed", 2),
    ("ERROR", "Database connection failed", 3),
]


# Time complexity: O(1): calculate the start and end timestamps.
def _five_year_window(end_time: datetime) -> tuple[datetime, datetime]:
    """Return a window from midnight five calendar years before end_time to end_time."""
    if end_time.tzinfo is not None:
        # The CSV format is timezone-naive. Convert aware values to UTC first.
        from datetime import timezone
        end_time = end_time.astimezone(timezone.utc).replace(tzinfo=None)
    end_time = end_time.replace(microsecond=0)
    try:
        start_time = end_time.replace(year=end_time.year - 5, month=end_time.month,
                                      day=end_time.day, hour=0, minute=0, second=0)
    except ValueError:
        # Handles February 29 when the date five years earlier is not a leap day.
        start_time = end_time.replace(year=end_time.year - 5, day=28,
                                      hour=0, minute=0, second=0)
    return start_time, end_time


# Time complexity: O(N log N): generate N records and sort them chronologically before writing.
def generate_synthetic_logs(
    output_path: str | Path,
    count: int = 10_000,
    seed: int = 20261020,
    end_time: datetime | None = None,
) -> Path:
    """Write ``count`` unique synthetic records spread over the previous five years.

    Exactly 30 event descriptions are available. When ``count`` is at least 30,
    every event type is included at least once; remaining event types are chosen
    using their weights. Timestamps are spread across the five-year window and
    records are written in chronological order. The first and last timestamps
    mark the window boundaries when at least two records are generated.

    ``end_time`` is an optional testing hook. Leaving it unset uses the current
    local system time, which makes the generated dataset cover the latest five
    years when the app's Generate Dataset button is used.
    """
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError("count must be a positive integer")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    start_time, end_time = _five_year_window(end_time or datetime.now())
    duration_seconds = int((end_time - start_time).total_seconds())
    if duration_seconds < 1:
        raise ValueError("end_time must be later than the start of the five-year window")

    ips = [f"192.168.{subnet}.{host}" for subnet in range(1, 5) for host in range(1, 65)]
    templates = [(severity, event) for severity, event, _weight in EVENT_TEMPLATES]
    weights = [weight for _severity, _event, weight in EVENT_TEMPLATES]

    if count >= len(templates):
        selected_events = list(templates)
        selected_events.extend(rng.choices(templates, weights=weights, k=count - len(templates)))
    else:
        selected_events = rng.sample(templates, k=count)
    rng.shuffle(selected_events)

    # Include both endpoints for datasets with at least two records so the
    # five-year coverage is visible and easy to verify in the generated CSV.
    if count == 1:
        seconds = [rng.randint(0, duration_seconds)]
    else:
        seconds = [0, duration_seconds]
        seconds.extend(rng.randint(0, duration_seconds) for _ in range(count - 2))
        rng.shuffle(seconds)

    rows: list[dict[str, str | int]] = []
    for index, ((severity, event_text), offset_seconds) in enumerate(zip(selected_events, seconds), start=1):
        timestamp = (start_time + timedelta(seconds=offset_seconds)).strftime("%Y-%m-%d %H:%M:%S")
        rows.append({
            "event_id": index,
            "timestamp": timestamp,
            "source_ip": rng.choice(ips),
            "severity": severity,
            "event": event_text,
        })

    rows.sort(key=lambda row: (str(row["timestamp"]), int(row["event_id"])))
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return destination
