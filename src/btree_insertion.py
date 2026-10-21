"""Teammate 2: B-Tree insertion and node splitting algorithms."""
from __future__ import annotations

from bisect import bisect_left
from typing import Any

from .btree_core import BTreeNode


class BTreeInsertionMixin:
    """Insertion methods composed into the public BTree class."""

    # Time complexity: O(log n): check for an existing key and insert along a path, splitting as needed.
    def insert(self, key: Any, value: Any) -> bool:
        """Insert key/value. Update an existing key; return True only if new."""
        existing = self.search_item(key)
        if existing is not None:
            existing[0].values[existing[1]] = value
            return False

        root = self.root
        if len(root.keys) == 2 * self.t - 1:
            new_root = BTreeNode(leaf=False)
            new_root.children.append(root)
            self._split_child(new_root, 0)
            self.root = new_root
        self._insert_non_full(self.root, key, value)
        return True

    # Time complexity: O(log n): descend one root-to-leaf path; t is fixed.
    def _insert_non_full(self, node: BTreeNode, key: Any, value: Any) -> None:
        index = bisect_left(node.keys, key)
        if node.leaf:
            node.keys.insert(index, key)
            node.values.insert(index, value)
            return

        if len(node.children[index].keys) == 2 * self.t - 1:
            self._split_child(node, index)
            if key > node.keys[index]:
                index += 1
            elif key == node.keys[index]:
                node.values[index] = value
                return
        self._insert_non_full(node.children[index], key, value)

    # Time complexity: O(t), or O(1) for this implementation with fixed minimum degree t.
    def _split_child(self, parent: BTreeNode, index: int) -> None:
        """Split a full child of parent at child index."""
        degree = self.t
        full_child = parent.children[index]
        right = BTreeNode(leaf=full_child.leaf)

        median_key = full_child.keys[degree - 1]
        median_value = full_child.values[degree - 1]
        right.keys = full_child.keys[degree:]
        right.values = full_child.values[degree:]
        full_child.keys = full_child.keys[: degree - 1]
        full_child.values = full_child.values[: degree - 1]

        if not full_child.leaf:
            right.children = full_child.children[degree:]
            full_child.children = full_child.children[:degree]

        parent.keys.insert(index, median_key)
        parent.values.insert(index, median_value)
        parent.children.insert(index + 1, right)
