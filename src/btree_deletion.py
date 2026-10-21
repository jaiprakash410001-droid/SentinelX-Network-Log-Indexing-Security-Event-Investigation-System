"""Teammate 3: B-Tree deletion, borrowing, merging, and rebalancing."""
from __future__ import annotations

from bisect import bisect_left
from typing import Any

from .btree_core import BTreeNode


class BTreeDeletionMixin:
    """Deletion and rebalancing methods composed into the public BTree class."""

    # Time complexity: O(log n): check presence, delete along a path, and adjust the root if required.
    def delete(self, key: Any) -> bool:
        """Delete key if present; return True if deleted, otherwise False."""
        self._metrics["delete_calls"] += 1
        if not self.contains(key):
            self._metrics["missing_deletes"] += 1
            return False
        self._delete_from_node(self.root, key)
        if len(self.root.keys) == 0 and not self.root.leaf:
            self.root = self.root.children[0]
        self._size -= 1
        self._metrics["successful_deletes"] += 1
        return True

    # Time complexity: O(log n): descend one path with constant-time local rebalancing for fixed t.
    def _delete_from_node(self, node: BTreeNode, key: Any) -> None:
        index = bisect_left(node.keys, key)

        if index < len(node.keys) and node.keys[index] == key:
            if node.leaf:
                node.keys.pop(index)
                node.values.pop(index)
            else:
                self._delete_internal_key(node, index)
            return

        if node.leaf:
            return  # Public delete checks presence first; this is defensive.

        was_last_child = index == len(node.keys)
        if len(node.children[index].keys) < self.t:
            self._fill_child(node, index)

        if was_last_child and index > len(node.keys):
            self._delete_from_node(node.children[index - 1], key)
        else:
            self._delete_from_node(node.children[index], key)

    # Time complexity: O(log n): predecessor/successor search or merge followed by deletion.
    def _delete_internal_key(self, node: BTreeNode, index: int) -> None:
        key = node.keys[index]
        left_child = node.children[index]
        right_child = node.children[index + 1]

        if len(left_child.keys) >= self.t:
            predecessor_key, predecessor_value = self._maximum_item(left_child)
            node.keys[index] = predecessor_key
            node.values[index] = predecessor_value
            self._delete_from_node(left_child, predecessor_key)
        elif len(right_child.keys) >= self.t:
            successor_key, successor_value = self._minimum_item(right_child)
            node.keys[index] = successor_key
            node.values[index] = successor_value
            self._delete_from_node(right_child, successor_key)
        else:
            merged = self._merge_children(node, index)
            self._delete_from_node(merged, key)

    # Time complexity: O(log n): follow the rightmost path to a leaf.
    @staticmethod
    def _maximum_item(node: BTreeNode) -> tuple[Any, Any]:
        while not node.leaf:
            node = node.children[-1]
        return node.keys[-1], node.values[-1]

    # Time complexity: O(log n): follow the leftmost path to a leaf.
    @staticmethod
    def _minimum_item(node: BTreeNode) -> tuple[Any, Any]:
        while not node.leaf:
            node = node.children[0]
        return node.keys[0], node.values[0]

    # Time complexity: O(t), or O(1) for fixed t; select a sibling borrow or merge.
    def _fill_child(self, parent: BTreeNode, index: int) -> None:
        if index > 0 and len(parent.children[index - 1].keys) >= self.t:
            self._borrow_from_previous(parent, index)
        elif index < len(parent.children) - 1 and len(parent.children[index + 1].keys) >= self.t:
            self._borrow_from_next(parent, index)
        elif index < len(parent.children) - 1:
            self._merge_children(parent, index)
        else:
            self._merge_children(parent, index - 1)

    # Time complexity: O(t), or O(1) for fixed t; move keys and child references within bounded nodes.
    def _borrow_from_previous(self, parent: BTreeNode, index: int) -> None:
        self._metrics["borrow_from_left"] += 1
        child = parent.children[index]
        sibling = parent.children[index - 1]
        child.keys.insert(0, parent.keys[index - 1])
        child.values.insert(0, parent.values[index - 1])
        if not child.leaf:
            child.children.insert(0, sibling.children.pop())
        parent.keys[index - 1] = sibling.keys.pop()
        parent.values[index - 1] = sibling.values.pop()

    # Time complexity: O(t), or O(1) for fixed t; move keys and child references within bounded nodes.
    def _borrow_from_next(self, parent: BTreeNode, index: int) -> None:
        self._metrics["borrow_from_right"] += 1
        child = parent.children[index]
        sibling = parent.children[index + 1]
        child.keys.append(parent.keys[index])
        child.values.append(parent.values[index])
        if not child.leaf:
            child.children.append(sibling.children.pop(0))
        parent.keys[index] = sibling.keys.pop(0)
        parent.values[index] = sibling.values.pop(0)

    # Time complexity: O(t), or O(1) for fixed t; merge bounded node contents.
    def _merge_children(self, parent: BTreeNode, index: int) -> BTreeNode:
        self._metrics["merges"] += 1
        left = parent.children[index]
        right = parent.children[index + 1]
        left.keys.append(parent.keys.pop(index))
        left.values.append(parent.values.pop(index))
        left.keys.extend(right.keys)
        left.values.extend(right.values)
        if not left.leaf:
            left.children.extend(right.children)
        parent.children.pop(index + 1)
        return left
