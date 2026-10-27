"""B-Tree node structure, search, traversal, validation, and metrics."""

from __future__ import annotations

from bisect import bisect_left
from typing import Any, Optional


class BTreeNode:
    """Represents a node in a B-Tree."""

    def __init__(self, leaf: bool = True) -> None:
        self.keys: list[Any] = []
        self.values: list[Any] = []
        self.children: list[BTreeNode] = []
        self.leaf = leaf

    def __repr__(self) -> str:
        return f"BTreeNode(keys={self.keys!r}, leaf={self.leaf})"


class BTreeCoreMixin:
    """Provides B-Tree initialization, searching, traversal, and validation."""

    def __init__(self, min_degree: int = 3) -> None:
        if (
            not isinstance(min_degree, int)
            or isinstance(min_degree, bool)
            or min_degree < 2
        ):
            raise ValueError(
                "min_degree must be an integer greater than or equal to 2"
            )

        self.t = min_degree
        self.root = BTreeNode(leaf=True)
        self._size = 0

        self._metrics = {
            "search_calls": 0,
            "insert_calls": 0,
            "delete_calls": 0,
            "successful_deletes": 0,
            "missing_deletes": 0,
            "splits": 0,
            "merges": 0,
            "borrow_from_left": 0,
            "borrow_from_right": 0,
        }

    # -------------------- Searching --------------------

    def search_item(self, key: Any) -> Optional[tuple[BTreeNode, int]]:
        """Return the node and index containing a key, or None."""
        self._metrics["search_calls"] += 1

        node = self.root

        while True:
            index = bisect_left(node.keys, key)

            if index < len(node.keys) and node.keys[index] == key:
                return node, index

            if node.leaf:
                return None

            node = node.children[index]

    def search(self, key: Any) -> Any:
        """Return the value associated with a key, or None if absent."""
        result = self.search_item(key)

        if result is None:
            return None

        node, index = result
        return node.values[index]

    def contains(self, key: Any) -> bool:
        """Return whether the key exists in the tree."""
        return self.search_item(key) is not None

    def search_path(self, key: Any) -> list[BTreeNode]:
        """Return the nodes visited while searching for a key.

        The path includes the node containing the key, when found, or the leaf
        where the search concludes when the key is absent.
        """
        self._metrics["search_calls"] += 1
        path: list[BTreeNode] = []
        node = self.root

        while True:
            path.append(node)
            index = bisect_left(node.keys, key)

            if index < len(node.keys) and node.keys[index] == key:
                return path

            if node.leaf:
                return path

            node = node.children[index]

    def search_with_comparisons(self, key: Any) -> tuple[Any, int]:
        """Return the value and number of key comparisons performed."""
        self._metrics["search_calls"] += 1

        node = self.root
        comparisons = 0

        while True:
            low = 0
            high = len(node.keys) - 1
            found_index: Optional[int] = None

            while low <= high:
                middle = (low + high) // 2
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

    # -------------------- Traversal --------------------

    def items(self) -> list[tuple[Any, Any]]:
        """Return all key-value pairs in sorted order."""
        result: list[tuple[Any, Any]] = []
        self._traverse(self.root, result)
        return result

    def _traverse(
        self, node: BTreeNode, result: list[tuple[Any, Any]]
    ) -> None:
        for index, key in enumerate(node.keys):
            if not node.leaf:
                self._traverse(node.children[index], result)

            result.append((key, node.values[index]))

        if not node.leaf:
            self._traverse(node.children[-1], result)

    # -------------------- Range Queries --------------------

    def range_items(
        self, low: Any, high: Any
    ) -> list[tuple[Any, Any]]:
        """Return sorted key-value pairs whose keys are within [low, high]."""
        if low > high:
            return []

        result: list[tuple[Any, Any]] = []
        self._range_walk(self.root, low, high, result)
        return result

    def _range_walk(
        self,
        node: BTreeNode,
        low: Any,
        high: Any,
        result: list[tuple[Any, Any]],
    ) -> None:
        index = 0

        while index < len(node.keys) and node.keys[index] < low:
            index += 1

        if not node.leaf:
            self._range_walk(node.children[index], low, high, result)

        while index < len(node.keys) and node.keys[index] <= high:
            result.append((node.keys[index], node.values[index]))

            if not node.leaf:
                self._range_walk(
                    node.children[index + 1], low, high, result
                )

            index += 1

    # -------------------- Tree Statistics --------------------

    def height(self) -> int:
        """Return the tree height in levels; an empty tree has height 0."""
        if not self.root.keys and self.root.leaf:
            return 0

        height = 1
        node = self.root

        while not node.leaf:
            height += 1
            node = node.children[0]

        return height

    def node_count(self) -> int:
        """Return the number of nodes in the tree."""

        def count(node: BTreeNode) -> int:
            return 1 + sum(count(child) for child in node.children)

        if not self.root.keys and self.root.leaf:
            return 0

        return count(self.root)

    def structure_stats(self) -> dict[str, Any]:
        """Return structural statistics about the B-Tree."""
        stats = {
            "nodes": 0,
            "keys": 0,
            "leaf_nodes": 0,
            "internal_nodes": 0,
            "average_fill_percent": 0.0,
        }

        if not self.root.keys and self.root.leaf:
            return stats

        total_capacity = 0

        def visit(node: BTreeNode) -> None:
            nonlocal total_capacity

            stats["nodes"] += 1
            stats["keys"] += len(node.keys)
            total_capacity += 2 * self.t - 1

            if node.leaf:
                stats["leaf_nodes"] += 1
            else:
                stats["internal_nodes"] += 1
                for child in node.children:
                    visit(child)

        visit(self.root)

        if total_capacity:
            stats["average_fill_percent"] = (
                stats["keys"] / total_capacity
            ) * 100.0

        return stats

    # -------------------- Metrics --------------------

    def metrics_snapshot(self) -> dict[str, int]:
        """Return a copy of the current operation metrics."""
        return self._metrics.copy()

    def reset_metrics(self) -> None:
        """Reset all operation metrics to zero."""
        for metric in self._metrics:
            self._metrics[metric] = 0

    # -------------------- Validation --------------------

    def validation_errors(self) -> list[str]:
        """Return a list of B-Tree invariant violations, if any."""
        errors: list[str] = []
        leaf_depths: set[int] = set()

        def visit(
            node: BTreeNode,
            depth: int,
            is_root: bool,
            lower: Any = None,
            upper: Any = None,
        ) -> None:
            if len(node.keys) != len(node.values):
                errors.append(
                    "A node has a different number of keys and values"
                )

            if len(node.keys) > 2 * self.t - 1:
                errors.append("A node exceeds the maximum key count")

            if not is_root and len(node.keys) < self.t - 1:
                errors.append("A non-root node has too few keys")

            if any(
                node.keys[i] >= node.keys[i + 1]
                for i in range(len(node.keys) - 1)
            ):
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
                errors.append(
                    "An internal node must have one more child than keys"
                )
                return

            for index, child in enumerate(node.children):
                child_lower = lower if index == 0 else node.keys[index - 1]
                child_upper = (
                    upper if index == len(node.keys) else node.keys[index]
                )

                visit(
                    child,
                    depth + 1,
                    False,
                    child_lower,
                    child_upper,
                )

        if not self.root.keys and self.root.leaf:
            if self.root.children:
                errors.append("An empty root leaf must not have children")

            return errors

        visit(self.root, 0, True)

        if len(leaf_depths) > 1:
            errors.append("All leaves must be at the same depth")

        return errors

    def validate(self) -> bool:
        """Return True if the B-Tree satisfies its structural invariants."""
        return not self.validation_errors()

    def __len__(self) -> int:
        """Return the number of key-value pairs."""
        return len(self.items())
