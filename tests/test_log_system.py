"""Integration tests for log loading, indexes, queries and duplicate handling."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.log_system import LogInvestigationSystem
from src.models import LogRecord

ROOT = Path(__file__).resolve().parents[1]


class LogSystemTests(unittest.TestCase):
    # Time complexity: O(1): construct an empty test system.
    def setUp(self):
        self.system = LogInvestigationSystem(min_degree=2)

    # Time complexity: O(N log N): load the sample and rebuild its indexes.
    def test_load_sample_file(self):
        report = self.system.load_csv(ROOT / "data" / "sample_logs.csv")
        self.assertEqual(report.loaded_rows, 15)
        self.assertEqual(report.duplicate_ids, 0)
        self.assertEqual(report.invalid_rows, 0)
        self.assertTrue(self.system.is_consistent())
        self.assertEqual(self.system.search_by_id(101).event, "Successful login")
        self.assertIsNone(self.system.search_by_id(99999))

    # Time complexity: O(N log N): load accepted records and rebuild the indexes.
    def test_duplicate_and_invalid_rows_match_expected_output(self):
        report = self.system.load_csv(ROOT / "data" / "test_logs_with_duplicates.csv")
        self.assertEqual(report.summary(),
                         "Rows read: 7\nRecords loaded: 4\n"
                         "Duplicate IDs skipped: 1\nInvalid rows skipped: 2")
        self.assertEqual(sorted(self.system.store.records), [201, 202, 203, 205])
        self.assertTrue(self.system.is_consistent())
        self.assertEqual(len(self.system.time_range("2026-10-20 09:01:00",
                                                    "2026-10-20 09:01:00")), 2)

    # Time complexity: O(N log N): load/index records, then run the range query.
    def test_range_query_includes_boundaries_and_is_chronological(self):
        self.system.load_csv(ROOT / "data" / "sample_logs.csv")
        results = self.system.time_range("2026-10-20 09:02:15", "2026-10-20 09:04:02")
        self.assertEqual([record.event_id for record in results], [102, 103, 104])

    # Time complexity: O(N): retrieve and filter the sample records.
    def test_filters(self):
        self.system.load_csv(ROOT / "data" / "sample_logs.csv")
        all_records = self.system.all_chronological()
        high = self.system.filter_records(all_records, severity="high")
        self.assertTrue(high)
        self.assertTrue(all(record.severity == "HIGH" for record in high))
        ip_matches = self.system.filter_records(all_records, source_ip="192.168.1.8")
        self.assertTrue(ip_matches)
        self.assertTrue(all(record.source_ip == "192.168.1.8" for record in ip_matches))

    # Time complexity: O(N log N): load records, test updates, and verify index consistency.
    def test_add_duplicate_and_delete_sync_indexes(self):
        self.system.load_csv(ROOT / "data" / "sample_logs.csv")
        with self.assertRaises(ValueError):
            self.system.add_record(LogRecord(101, "2026-10-20 10:00:00", "127.0.0.1", "INFO", "duplicate"))
        self.assertTrue(self.system.delete_record(101))
        self.assertIsNone(self.system.search_by_id(101))
        self.assertFalse(self.system.delete_record(101))
        self.assertTrue(self.system.is_consistent())
        self.assertEqual(len(self.system.all_chronological()), 14)

    # Time complexity: O(R + N log N): reject invalid IP rows and index N accepted rows.
    def test_invalid_ip_is_rejected_when_creating_log(self):
        """Reject invalid IPs in both direct log creation and CSV imports."""
        with self.assertRaisesRegex(ValueError, "valid IPv4 or IPv6"):
            LogRecord(9001, "2026-10-20 10:00:00", "999.999.1.1", "INFO", "Bad IP")

        with self.assertRaisesRegex(ValueError, "valid IPv4 or IPv6"):
            LogRecord(9002, "2026-10-20 10:00:00", "not-an-ip", "INFO", "Bad IP")

        valid_record = LogRecord(
            9003, "2026-10-20 10:00:00", "2001:db8::1", "INFO", "Valid IPv6"
        )
        self.assertEqual(valid_record.source_ip, "2001:db8::1")

        # CSV import must count an invalid-IP row as invalid and continue with valid rows.
        with TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "ip_validation.csv"
            csv_path.write_text(
                "event_id,timestamp,source_ip,severity,event\n"
                "9011,2026-10-20 10:00:00,999.999.1.1,HIGH,Invalid IP\n"
                "9012,2026-10-20 10:01:00,192.0.2.10,INFO,Valid IP\n",
                encoding="utf-8",
            )
            report = self.system.load_csv(csv_path)
            self.assertEqual(report.loaded_rows, 1)
            self.assertEqual(report.invalid_rows, 1)
            self.assertIsNone(self.system.search_by_id(9011))
            self.assertIsNotNone(self.system.search_by_id(9012))

    # Time complexity: O(N log N): load the test dataset; invalid range validation itself is O(1).
    def test_invalid_time_range(self):
        self.system.load_csv(ROOT / "data" / "sample_logs.csv")
        with self.assertRaises(ValueError):
            self.system.time_range("2026-10-20 10:00:00", "2026-10-20 09:00:00")

    # Time complexity: O(N + u log u): scan test records and sort qualifying IPs.
    def test_repeated_failed_login_rule(self):
        self.system.load_csv(ROOT / "data" / "sample_logs.csv")
        patterns = self.system.queries.repeated_failed_logins(minimum_attempts=3)
        self.assertEqual(patterns, [("192.168.1.8", 5)])


if __name__ == "__main__":
    unittest.main()
