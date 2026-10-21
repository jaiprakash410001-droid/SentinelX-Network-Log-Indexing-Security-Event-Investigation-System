"""Teammate 1: B-Tree node structure, search, traversal, and validation.

This module contains the structural and read/query operations used by BTree.
"""
from __future__ import annotations

from bisect import bisect_left
from typing import Any, Optional


class BTreeNode:
    """One node in a B-Tree. Keys and values share the same positions."""

    # Time complexity: O(1): initialize the empty root and minimum degree.
    def __init__(self, leaf: bool = True) -> None:
        self.keys: list[Any] = []
        self.values: list[Any] = []
        self.children: list[BTreeNode] = []
        self.leaf = leaf

    # Time complexity: O(t): render the keys in one node; O(1) when the minimum degree t is fixed.
    def __repr__(self) -> str:
        return f"BTreeNode(keys={self.keys!r}, leaf={self.leaf})"


class BTreeCoreMixin:
    """Shared B-Tree initialization, search, traversal, and validation methods."""

    # Time complexity: O(1): initialize the empty root and minimum degree.
    def __init__(self, min_degree: int = 3) -> None:
        if not isinstance(min_degree, int) or min_degree < 2:
            raise ValueError("min_degree must be an integer greater than or equal to 2")
        self.t = min_degree
        self.root = BTreeNode(leaf=True)

    # Time complexity: O(log n): visit one root-to-leaf path; node-local binary search is O(log t).
    def search_item(self, key: Any) -> Optional[tuple[BTreeNode, int]]:
        """Return (node, index) for key, or None if key is not present."""
        node = self.root
        while True:
            index = bisect_left(node.keys, key)
            if index < len(node.keys) and node.keys[index] == key:
                return node, index
            if node.leaf:
                return None
            node = node.children[index]

    # Time complexity: O(log n): delegates to search_item and performs constant-time value access.
    def search(self, key: Any) -> Any:
        """Return the value for key, or None if key is absent."""
        result = self.search_item(key)
        return None if result is None else result[0].values[result[1]]

    # Time complexity: O(log n): delegates to search_item.
    def contains(self, key: Any) -> bool:
        """Return whether key exists in the tree."""
        return self.search_item(key) is not None

    # Time complexity: O(log n): binary-search node keys along a path of logarithmic height.
    def search_with_comparisons(self, key: Any) -> tuple[Any, int]:
        """Search for key and return (value-or-None, key-comparison count).

        The count is useful for educational benchmarks. One comparison means
        one logical comparison of the target key with a midpoint key in a node.
        """
        node = self.root
        comparisons = 0
        while True:
            low, high = 0, len(node.keys) - 1
            found_index: Optional[int] = None
            insertion_index = 0
            while low <= high:
                middle = (low + high) // 2
                # Count one logical key comparison per midpoint probe.
                comparisons += 1
                if node.keys[middle] == key:
                    found_index = middle
                    break
                if node.keys[middle] < key:
                    low = middle + 1
                else:
                    high = middle - 1
            if found_index is not None:
                return node.values[found_index], comparisons
            insertion_index = low
            if node.leaf:
                return None, comparisons
            node = node.children[insertion_index]

    # Time complexity: O(n): returns every key-value pair in sorted order.
    def items(self) -> list[tuple[Any, Any]]:
        """Return all key/value pairs in ascending key order."""
        result: list[tuple[Any, Any]] = []
        self._traverse(self.root, result)
        return result

    # Time complexity: O(s): visits each key in the subtree containing s keys once.
    def _traverse(self, node: BTreeNode, result: list[tuple[Any, Any]]) -> None:
        for index, key in enumerate(node.keys):
            if not node.leaf:
                self._traverse(node.children[index], result)
            result.append((key, node.values[index]))
        if not node.leaf:
            self._traverse(node.children[-1], result)

    # Time complexity: O(log n + k): locate the range and return its k matching keys.
    def range_items(self, low: Any, high: Any) -> list[tuple[Any, Any]]:
        """Return key/value pairs where low <= key <= high, in key order."""
        if low > high:
            return []
        result: list[tuple[Any, Any]] = []
        self._range_walk(self.root, low, high, result)
        return result

    # Time complexity: O(log n + k): visit boundary paths and the k keys in the requested range.
    def _range_walk(self, node: BTreeNode, low: Any, high: Any,
                    result: list[tuple[Any, Any]]) -> None:
        index = 0
        while index < len(node.keys) and node.keys[index] < low:
            index += 1

        if not node.leaf:
            self._range_walk(node.children[index], low, high, result)

        while index < len(node.keys) and node.keys[index] <= high:
            result.append((node.keys[index], node.values[index]))
            if not node.leaf:
                self._range_walk(node.children[index + 1], low, high, result)
            index += 1

    # Time complexity: O(log n): follow the leftmost path of the balanced tree.
    def height(self) -> int:
        """Return the number of node levels (empty tree has height 0)."""
        if not self.root.keys and self.root.leaf:
            return 0
        height = 1
        node = self.root
        while not node.leaf:
            height += 1
            node = node.children[0]
        return height

    # Time complexity: O(M): visit all M nodes; M is O(n) for fixed minimum degree.
    def node_count(self) -> int:
        """Return the number of nodes in the tree."""
        # Time complexity: O(M): recursively count each node in the subtree once.
        def count(node: BTreeNode) -> int:
            return 1 + sum(count(child) for child in node.children)
        if not self.root.keys and self.root.leaf:
            return 0
        return count(self.root)

    # Time complexity: O(n): check every key, child link, bound, and leaf depth.
    def validation_errors(self) -> list[str]:
        """Return all detected B-Tree invariant violations (empty if valid)."""
        errors: list[str] = []
        leaf_depths: set[int] = set()

        # Time complexity: O(s): validate each key and descendant in the current subtree.
        def visit(node: BTreeNode, depth: int, is_root: bool,
                  lower: Any = None, upper: Any = None) -> None:
            if len(node.keys) != len(node.values):
                errors.append("A node has a different number of keys and values")
            if len(node.keys) > 2 * self.t - 1:
                errors.append("A node exceeds the maximum key count")
            if not is_root and len(node.keys) < self.t - 1:
                errors.append("A non-root node has too few keys")
            if any(node.keys[i] >= node.keys[i + 1] for i in range(len(node.keys) - 1)):
                errors.append("Keys inside a node are not strictly increasing")
            for key in node.keys:
                if lower is not None and not lower < key:
                    errors.append("A key violates its lower bound")
                if upper is not None and not key < upper:
                    errors.append("A key violates its upper bound")

            if node.leaf:
                if node.children:
                    errors.append("A leaf node must not have children")
                leaf_depths.add(depth)
                return

            if len(node.children) != len(node.keys) + 1:
                errors.append("An internal node must have one more child than keys")
                return

            for index, child in enumerate(node.children):
                child_lower = lower if index == 0 else node.keys[index - 1]
                child_upper = upper if index == len(node.keys) else node.keys[index]
                visit(child, depth + 1, False, child_lower, child_upper)

        if not self.root.keys and self.root.leaf:
            if self.root.children:
                errors.append("An empty root leaf must not have children")
            return errors
        visit(self.root, 0, True)
        if len(leaf_depths) > 1:
            errors.append("All leaves must be at the same depth")
        return errors

    # Time complexity: O(n): run the complete invariant check.
    def validate(self) -> bool:
        """Return True when B-Tree invariants hold."""
        return not self.validation_errors()

    # Time complexity: O(n): currently calls items(), which traverses and builds a full list.
    def __len__(self) -> int:
        """Return the number of keys in the tree."""
        return len(self.items())
