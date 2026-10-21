"""Public B-Tree API assembled from teammate-owned implementation modules."""
from __future__ import annotations

from .btree_core import BTreeCoreMixin, BTreeNode
from .btree_deletion import BTreeDeletionMixin
from .btree_insertion import BTreeInsertionMixin


class BTree(BTreeCoreMixin, BTreeInsertionMixin, BTreeDeletionMixin):
    """B-Tree map with search, insertion, deletion, ranges, and validation.

    The implementation is split into modules so each teammate can own a clear
    algorithmic component while the rest of the application keeps importing BTree.
    """
    pass


__all__ = ["BTree", "BTreeNode"]
