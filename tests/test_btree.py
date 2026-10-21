"""Unit tests for the B-Tree's operations and structural invariants."""
import random
import unittest

from src.btree import BTree


class BTreeTests(unittest.TestCase):
    # Time complexity: O(1): exercise empty-tree operations.
    def test_empty_tree(self):
        tree = BTree(3)
        self.assertIsNone(tree.search(10))
        self.assertFalse(tree.delete(10))
        self.assertEqual(tree.items(), [])
        self.assertEqual(len(tree), 0)
        self.assertEqual(tree.height(), 0)
        self.assertTrue(tree.validate(), tree.validation_errors())

    # Time complexity: O(n^2) overall due to repeated full-tree validation on a small fixed test set.
    def test_insert_search_and_duplicate_update(self):
        tree = BTree(2)
        for key in [10, 20, 5, 6, 12, 30, 7, 17]:
            self.assertTrue(tree.insert(key, f"value-{key}"))
            self.assertTrue(tree.validate(), tree.validation_errors())
        self.assertEqual(tree.search(12), "value-12")
        self.assertIsNone(tree.search(99))
        self.assertFalse(tree.insert(12, "updated"))
        self.assertEqual(tree.search(12), "updated")
        self.assertEqual(len([key for key, _ in tree.items() if key == 12]), 1)

    # Time complexity: O(n^2) overall due to repeated validation while inserting the test keys.
    def test_range_query_is_inclusive_and_ordered(self):
        tree = BTree(2)
        for key in [20, 4, 10, 2, 8, 12, 18, 25, 30, 14]:
            tree.insert(key, str(key))
        self.assertEqual([key for key, _ in tree.range_items(8, 20)], [8, 10, 12, 14, 18, 20])
        self.assertEqual(tree.range_items(21, 19), [])
        self.assertEqual([key for key, _ in tree.range_items(-100, 1)], [])
        self.assertEqual([key for key, _ in tree.range_items(100, 200)], [])

    # Time complexity: O(n^2) overall because each insert/delete is followed by an O(n) validation.
    def test_delete_many_cases(self):
        tree = BTree(2)
        keys = list(range(1, 80))
        random.Random(2026).shuffle(keys)
        for key in keys:
            tree.insert(key, key * 10)
            self.assertTrue(tree.validate(), tree.validation_errors())
        deletion_order = list(range(1, 80))
        random.Random(99).shuffle(deletion_order)
        for key in deletion_order:
            self.assertTrue(tree.delete(key), f"Expected key {key} to be deleted")
            self.assertFalse(tree.contains(key))
            self.assertTrue(tree.validate(), f"After deleting {key}: {tree.validation_errors()}")
            self.assertEqual(len(tree), 78 - deletion_order.index(key))
        self.assertEqual(tree.items(), [])
        self.assertEqual(len(tree), 0)
        metrics = tree.metrics_snapshot()
        self.assertGreater(metrics["splits"], 0)
        self.assertGreater(metrics["merges"], 0)
        self.assertGreater(metrics["borrow_from_left"] + metrics["borrow_from_right"], 0)
        self.assertEqual(metrics["successful_deletes"], 79)
        self.assertEqual(tree.height(), 0)

    # Time complexity: O(qn) for q operations because each step validates and traverses the current tree.
    def test_random_operations_against_dictionary(self):
        randomizer = random.Random(12345)
        tree = BTree(3)
        expected = {}
        for _ in range(1200):
            key = randomizer.randint(0, 180)
            if randomizer.random() < 0.62:
                value = randomizer.randint(-1000, 1000)
                was_new = key not in expected
                self.assertEqual(tree.insert(key, value), was_new)
                expected[key] = value
            else:
                removed = key in expected
                self.assertEqual(tree.delete(key), removed)
                expected.pop(key, None)
            self.assertTrue(tree.validate(), tree.validation_errors())
            self.assertEqual(tree.items(), sorted(expected.items()))
            self.assertEqual(len(tree), len(expected))
            for probe in (0, key, 90, 180, 200):
                self.assertEqual(tree.search(probe), expected.get(probe))

    # Time complexity: O(n log n) overall to build the test tree and perform searches.
    def test_search_comparison_counter(self):
        tree = BTree(3)
        for key in range(1, 100):
            tree.insert(key, key)
        value, comparisons = tree.search_with_comparisons(55)
        self.assertEqual(value, 55)
        self.assertGreater(comparisons, 0)
        self.assertLess(comparisons, 30)

    # Time complexity: O(n log n) overall to build a tree and compare the counters with expected operations.
    def test_size_metrics_and_search_path(self):
        tree = BTree(2)
        self.assertEqual(len(tree), 0)
        self.assertEqual(tree.structure_stats()["nodes"], 0)

        for key in [10, 20, 5, 6, 12, 30, 7, 17, 3, 4, 2]:
            tree.insert(key, key)
        self.assertEqual(len(tree), 11)
        self.assertGreater(tree.metrics_snapshot()["splits"], 0)

        # Re-inserting a key updates its value but does not increase the key count.
        self.assertFalse(tree.insert(6, "updated"))
        self.assertEqual(len(tree), 11)
        self.assertEqual(tree.search(6), "updated")

        path = tree.search_path(17)
        self.assertTrue(path)
        self.assertIn(17, path[-1].keys)
        self.assertLessEqual(len(path), tree.height())

        summary = tree.structure_stats()
        self.assertEqual(summary["keys"], 11)
        self.assertEqual(summary["leaf_nodes"] + summary["internal_nodes"], summary["nodes"])
        self.assertGreater(summary["average_fill_percent"], 0)

        self.assertTrue(tree.delete(6))
        self.assertEqual(len(tree), 10)
        self.assertEqual(tree.metrics_snapshot()["successful_deletes"], 1)
        self.assertFalse(tree.delete(999))
        self.assertEqual(tree.metrics_snapshot()["missing_deletes"], 1)

        tree.reset_metrics()
        self.assertEqual(sum(tree.metrics_snapshot().values()), 0)
        self.assertEqual(len(tree), 10, "resetting metrics must not change the tree")

    # Time complexity: O(1): test constructor validation.
    def test_invalid_degree(self):
        with self.assertRaises(ValueError):
            BTree(1)


if __name__ == "__main__":
    unittest.main()
