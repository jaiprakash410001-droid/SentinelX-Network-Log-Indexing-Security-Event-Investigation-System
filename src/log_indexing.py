"""Teammate 4: log storage, B-Tree indexes, queries, and system integration."""
from __future__ import annotations

import csv
from math import inf
from pathlib import Path
from typing import Iterable

from .btree import BTree
from .models import LoadReport, LogRecord, normalize_timestamp


class LogStore:
    """Stores unique log records by event ID and imports CSV data safely."""

    REQUIRED_COLUMNS = {"event_id", "timestamp", "source_ip", "severity"}

    # Time complexity: O(1): initialize the record dictionary.
    def __init__(self) -> None:
        self.records: dict[int, LogRecord] = {}

    # Time complexity: O(1) expected: dictionary membership and insertion by event ID.
    def add(self, record: LogRecord) -> None:
        """Add a record or raise ValueError if its event ID already exists."""
        if record.event_id in self.records:
            raise ValueError(f"event ID {record.event_id} already exists")
        self.records[record.event_id] = record

    # Time complexity: O(1) expected: dictionary lookup by event ID.
    def get(self, event_id: int) -> LogRecord | None:
        """Return the record for an ID, or None when it does not exist."""
        return self.records.get(event_id)

    # Time complexity: O(1) expected: dictionary removal by event ID.
    def remove(self, event_id: int) -> LogRecord | None:
        """Remove and return a record, or None when the ID is missing."""
        return self.records.pop(event_id, None)

    # Time complexity: O(N): remove N stored records.
    def clear(self) -> None:
        """Remove all records from storage."""
        self.records.clear()

    # Time complexity: O(N log N): sort N event IDs and collect their records.
    def all_records(self) -> list[LogRecord]:
        """Return records ordered by event ID."""
        return [self.records[key] for key in sorted(self.records)]

    # Time complexity: O(R + N) expected for R input rows and N accepted unique records, excluding index rebuild.
    def load_csv(self, path: str | Path) -> LoadReport:
        """Replace current records with valid unique records from a CSV file.

        The first valid row for an event ID wins. Duplicate IDs and invalid rows
        are skipped and counted in the returned report. A missing/unreadable
        file raises OSError; a CSV missing required headers raises ValueError.
        """
        csv_path = Path(path)
        loaded: dict[int, LogRecord] = {}
        report = LoadReport()
        try:
            with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames is None:
                    raise ValueError("CSV file is empty or has no header row")
                headers = {header.strip().lower() for header in reader.fieldnames if header}
                missing = self.REQUIRED_COLUMNS - headers
                if missing:
                    raise ValueError("CSV is missing required columns: " + ", ".join(sorted(missing)))
                has_event = "event" in headers or "event_description" in headers
                if not has_event:
                    raise ValueError("CSV is missing required column: event (or event_description)")

                for line_number, row in enumerate(reader, start=2):
                    # Ignore completely blank lines.
                    if not any(str(value or "").strip() for value in row.values()):
                        continue
                    report.total_rows += 1
                    try:
                        record = LogRecord.from_mapping(row)
                    except ValueError as exc:
                        report.invalid_rows += 1
                        report.issues.append(f"Line {line_number}: {exc}")
                        continue
                    if record.event_id in loaded:
                        report.duplicate_ids += 1
                        report.issues.append(
                            f"Line {line_number}: duplicate event ID {record.event_id} skipped"
                        )
                        continue
                    loaded[record.event_id] = record
        except OSError:
            raise

        self.records = loaded
        report.loaded_rows = len(loaded)
        return report

class IndexManager:
    """Maintains synchronized B-Tree indexes for the records in LogStore."""

    # Time complexity: O(1): create two empty B-Tree indexes.
    def __init__(self, min_degree: int = 3) -> None:
        self.min_degree = min_degree
        self.event_id_index: BTree = BTree(min_degree)
        self.timestamp_index: BTree = BTree(min_degree)

    # Time complexity: O(log N): insert the event-ID and timestamp keys into two B-Trees.
    def add_record(self, record: LogRecord) -> None:
        """Index a record by event ID and (timestamp, event ID)."""
        self.event_id_index.insert(record.event_id, record.event_id)
        self.timestamp_index.insert((record.timestamp, record.event_id), record.event_id)

    # Time complexity: O(log N): delete the record keys from both B-Trees.
    def remove_record(self, record: LogRecord) -> None:
        """Remove a record's keys from both indexes."""
        self.event_id_index.delete(record.event_id)
        self.timestamp_index.delete((record.timestamp, record.event_id))

    # Time complexity: O(N log N): insert N records into each B-Tree index.
    def rebuild(self, records: list[LogRecord]) -> None:
        """Recreate both indexes from a list of records."""
        self.event_id_index = BTree(self.min_degree)
        self.timestamp_index = BTree(self.min_degree)
        for record in records:
            self.add_record(record)

    # Time complexity: O(N log N): validate the two trees and search both indexes for each record.
    def is_consistent(self, records: dict[int, LogRecord]) -> bool:
        """Check that each stored record appears in both indexes."""
        if len(self.event_id_index) != len(records):
            return False
        if len(self.timestamp_index) != len(records):
            return False
        if not self.event_id_index.validate() or not self.timestamp_index.validate():
            return False
        for event_id, record in records.items():
            if self.event_id_index.search(event_id) != event_id:
                return False
            if self.timestamp_index.search((record.timestamp, event_id)) != event_id:
                return False
        return True

class QueryEngine:
    """Performs exact, range, filter and chronological log queries."""

    # Time complexity: O(1): retain references to the record store and indexes.
    def __init__(self, store: LogStore, indexes: IndexManager) -> None:
        self.store = store
        self.indexes = indexes

    # Time complexity: O(log N): B-Tree lookup plus expected O(1) record-store lookup.
    def search_by_id(self, event_id: int) -> LogRecord | None:
        """Find one record through the event-ID B-Tree."""
        found_id = self.indexes.event_id_index.search(event_id)
        return None if found_id is None else self.store.get(found_id)

    # Time complexity: O(log N + k): retrieve k entries from the timestamp B-Tree range.
    def time_range(self, start: str, end: str) -> list[LogRecord]:
        """Return records whose timestamps are in the inclusive [start, end]."""
        start_normalized = normalize_timestamp(start)
        end_normalized = normalize_timestamp(end)
        if start_normalized > end_normalized:
            raise ValueError("start timestamp must be earlier than or equal to end timestamp")
        low = (start_normalized, -inf)
        high = (end_normalized, inf)
        indexed = self.indexes.timestamp_index.range_items(low, high)
        result: list[LogRecord] = []
        for _key, event_id in indexed:
            record = self.store.get(event_id)
            if record is not None:
                result.append(record)
        return result

    # Time complexity: O(N): traverse the timestamp index and retrieve every record.
    def all_chronological(self) -> list[LogRecord]:
        """Return all records ordered by timestamp and then event ID."""
        result: list[LogRecord] = []
        for _key, event_id in self.indexes.timestamp_index.items():
            record = self.store.get(event_id)
            if record is not None:
                result.append(record)
        return result

    # Time complexity: O(m): inspect the m records supplied to the filter.
    @staticmethod
    def filter_records(records: list[LogRecord], severity: str = "",
                       source_ip: str = "") -> list[LogRecord]:
        """Filter a result list by optional severity and source IP."""
        severity_normalized = severity.strip().upper()
        ip_normalized = source_ip.strip().casefold()
        return [
            record for record in records
            if (not severity_normalized or record.severity == severity_normalized)
            and (not ip_normalized or record.source_ip.casefold() == ip_normalized)
        ]

    # Time complexity: O(N + u log u): scan records and sort u qualifying source IPs.
    def repeated_failed_logins(self, minimum_attempts: int = 3) -> list[tuple[str, int]]:
        """Return (source IP, count) for IPs with repeated failed-login events.

        This is a simple educational rule, not a determination that an attack
        has occurred. The scan is O(n) over the stored log records.
        """
        if minimum_attempts < 1:
            raise ValueError("minimum_attempts must be at least 1")
        counts: dict[str, int] = {}
        for record in self.store.records.values():
            text = record.event.casefold()
            if "failed login" in text:
                counts[record.source_ip] = counts.get(record.source_ip, 0) + 1
        return sorted(
            [(ip, count) for ip, count in counts.items() if count >= minimum_attempts],
            key=lambda pair: (-pair[1], pair[0]),
        )

class LogInvestigationSystem:
    """Facade used by the GUI, tests and command-line tools."""

    # Time complexity: O(1): initialize storage, indexes, and query service.
    def __init__(self, min_degree: int = 3) -> None:
        self.store = LogStore()
        self.indexes = IndexManager(min_degree=min_degree)
        self.queries = QueryEngine(self.store, self.indexes)

    # Time complexity: O(R + N log N): load R rows, then rebuild both indexes for N accepted records.
    def load_csv(self, path: str | Path) -> LoadReport:
        """Load a CSV file, skip duplicate/invalid rows, and rebuild indexes."""
        report = self.store.load_csv(path)
        self.indexes.rebuild(self.store.all_records())
        return report

    # Time complexity: O(log N) normally; O(N log N) on the exceptional rollback/rebuild path.
    def add_record(self, record: LogRecord) -> None:
        """Add a unique record and update both B-Tree indexes."""
        self.store.add(record)
        try:
            self.indexes.add_record(record)
        except Exception:
            # Keep record storage and indexes consistent if indexing fails.
            self.store.remove(record.event_id)
            self.indexes.rebuild(self.store.all_records())
            raise

    # Time complexity: O(log N): remove one record from both indexes and the store.
    def delete_record(self, event_id: int) -> bool:
        """Delete a record and its keys from both indexes."""
        record = self.store.get(event_id)
        if record is None:
            return False
        self.indexes.remove_record(record)
        self.store.remove(event_id)
        return True

    # Time complexity: O(log N): delegate to indexed event-ID search.
    def search_by_id(self, event_id: int) -> LogRecord | None:
        return self.queries.search_by_id(event_id)

    # Time complexity: O(log N + k): delegate to the timestamp range query.
    def time_range(self, start: str, end: str) -> list[LogRecord]:
        return self.queries.time_range(start, end)

    # Time complexity: O(N): retrieve all records in timestamp order.
    def all_chronological(self) -> list[LogRecord]:
        return self.queries.all_chronological()

    # Time complexity: O(m): filter the m supplied records.
    def filter_records(self, records: list[LogRecord], severity: str = "",
                       source_ip: str = "") -> list[LogRecord]:
        return self.queries.filter_records(records, severity, source_ip)

    # Time complexity: O(N log N): check both indexes against the stored records.
    def is_consistent(self) -> bool:
        return self.indexes.is_consistent(self.store.records)
