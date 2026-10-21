"""Tests for synthetic dataset generation and the bundled 10k demonstration data."""
import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.log_generator import EVENT_TEMPLATES, generate_synthetic_logs
from src.log_system import LogInvestigationSystem

ROOT = Path(__file__).resolve().parents[1]


class LogGeneratorTests(unittest.TestCase):
    # Time complexity: O(N log N): generate and sort N test records.
    def test_generator_creates_requested_number_of_unique_records_over_five_years(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "generated.csv"
            fixed_end = datetime(2026, 10, 20, 12, 0, 0)
            returned = generate_synthetic_logs(path, count=250, seed=123, end_time=fixed_end)
            self.assertEqual(returned, path)
            with path.open("r", newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 250)
            ids = [int(row["event_id"]) for row in rows]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(set(ids), set(range(1, 251)))
            times = [datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S") for row in rows]
            self.assertEqual(times, sorted(times))
            self.assertEqual(times[0], datetime(2021, 10, 20, 0, 0, 0))
            self.assertEqual(times[-1], fixed_end)
            self.assertEqual(len(set(row["event"] for row in rows)), 30)

    # Time complexity: O(1): test count validation.
    def test_generator_rejects_invalid_count(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaises(ValueError):
                generate_synthetic_logs(Path(temporary_directory) / "bad.csv", count=0)

    # Time complexity: O(N log N): generate and sort the small test dataset.
    def test_generator_supports_small_counts(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = generate_synthetic_logs(
                Path(temporary_directory) / "small.csv", count=5, seed=7,
                end_time=datetime(2026, 10, 20, 12, 0, 0),
            )
            with path.open("r", newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 5)
            self.assertEqual(len(set(row["event"] for row in rows)), 5)

    # Time complexity: O(E): inspect the E event templates.
    def test_event_library_contains_30_unique_event_descriptions(self):
        self.assertEqual(len(EVENT_TEMPLATES), 30)
        self.assertEqual(len({event for _severity, event, _weight in EVENT_TEMPLATES}), 30)

    # Time complexity: O(N log N): load and index the 10,000 bundled records.
    def test_bundled_10000_dataset_loads_and_indexes_consistently(self):
        path = ROOT / "data" / "sample_logs_10000.csv"
        self.assertTrue(path.exists(), "The 10,000-record demonstration dataset must be bundled")
        with path.open("r", newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 10_000)
        self.assertEqual(len({int(row["event_id"]) for row in rows}), 10_000)
        self.assertEqual(len({row["event"] for row in rows}), 30)
        timestamps = [datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S") for row in rows]
        self.assertEqual(timestamps, sorted(timestamps))
        self.assertEqual(timestamps[0], datetime(2021, 10, 20, 0, 0, 0))
        self.assertEqual(timestamps[-1].date(), datetime(2026, 10, 20).date())

        system = LogInvestigationSystem(min_degree=3)
        report = system.load_csv(path)
        self.assertEqual(report.total_rows, 10_000)
        self.assertEqual(report.loaded_rows, 10_000)
        self.assertEqual(report.duplicate_ids, 0)
        self.assertEqual(report.invalid_rows, 0)
        self.assertTrue(system.is_consistent())
        self.assertIsNotNone(system.search_by_id(1))
        self.assertIsNotNone(system.search_by_id(10_000))
        self.assertEqual(len(system.all_chronological()), 10_000)
        self.assertEqual(len(system.time_range("2021-10-20 00:00:00", "2021-10-20 00:00:00")), 1)
        self.assertEqual(len(system.time_range("2026-10-20 19:30:00", "2026-10-20 19:30:00")), 1)


if __name__ == "__main__":
    unittest.main()
