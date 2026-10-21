"""Compare B-Tree search with linear search for increasing dataset sizes.

Run from the project root with: python -m benchmarks.benchmark
"""
from __future__ import annotations

import random
import statistics
import time

from src.btree import BTree


# Time complexity: O(n log n + qn): build an n-key B-Tree and run q searches against both indexed and linear search.
def benchmark_size(size: int, query_count: int = 100) -> dict[str, float | int]:
    """Build a B-Tree and measure exact-key searches for a dataset size."""
    tree = BTree(min_degree=8)
    keys = list(range(size))
    for key in keys:
        tree.insert(key, key)

    rng = random.Random(2026 + size)
    targets = [rng.randrange(size) for _ in range(query_count)]

    btree_times: list[float] = []
    btree_comparisons = 0
    for target in targets:
        start = time.perf_counter_ns()
        value, comparisons = tree.search_with_comparisons(target)
        btree_times.append((time.perf_counter_ns() - start) / 1_000_000)
        if value != target:
            raise AssertionError(f"B-Tree returned wrong value for key {target}")
        btree_comparisons += comparisons

    linear_times: list[float] = []
    linear_comparisons = 0
    for target in targets:
        start = time.perf_counter_ns()
        found = None
        for key in keys:
            linear_comparisons += 1
            if key == target:
                found = key
                break
        linear_times.append((time.perf_counter_ns() - start) / 1_000_000)
        if found != target:
            raise AssertionError(f"Linear search returned wrong value for key {target}")

    return {
        "size": size,
        "queries": query_count,
        "btree_ms": statistics.mean(btree_times),
        "linear_ms": statistics.mean(linear_times),
        "btree_comparisons_per_query": btree_comparisons / query_count,
        "linear_comparisons_per_query": linear_comparisons / query_count,
        "height": tree.height(),
    }


# Time complexity: O(Nmax log Nmax + q Nmax): run benchmarks up to the largest configured dataset size.
def main() -> None:
    print("B-Tree vs Linear Search (measured on this machine)")
    print("Dataset | Queries | B-Tree avg ms | Linear avg ms | B-Tree comps/query | Linear comps/query | Height")
    for size in (1_000, 10_000, 100_000):
        result = benchmark_size(size, query_count=100)
        print(
            f"{result['size']:>7} | {result['queries']:>7} | "
            f"{result['btree_ms']:>13.6f} | {result['linear_ms']:>13.6f} | "
            f"{result['btree_comparisons_per_query']:>18.2f} | "
            f"{result['linear_comparisons_per_query']:>18.2f} | {result['height']}"
        )


if __name__ == "__main__":
    main()
