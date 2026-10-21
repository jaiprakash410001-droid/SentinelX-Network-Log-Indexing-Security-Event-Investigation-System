# Team Responsibilities (4 Members)

The main algorithm files are separated so each teammate can make meaningful commits to an independently owned file. `src/btree.py` is a small compatibility facade that keeps the application's public `BTree` import stable.

| Member | Primary file to own and push | Responsibilities | What to explain in the viva |
|---|---|---|---|
| **Teammate 1** | `src/btree_core.py` | B-Tree node structure, initialization, searching, traversal, range traversal, height/node counting, and invariant validation. | Multiway-tree representation, search path, sorted traversal, and validation rules. |
| **Teammate 2** | `src/btree_insertion.py` | Insertion, full-node detection, node splitting, median promotion, and root splitting. | How insertion preserves B-Tree order and balance. |
| **Teammate 3** | `src/btree_deletion.py` | Deletion, predecessor/successor replacement, borrowing, merging, and root reduction. | Underflow cases and how each rebalancing operation preserves the invariants. |
| **Teammate 4** | `src/log_indexing.py` | Log storage/CSV loading, event-ID and timestamp indexes, range queries, filters, index consistency, and the application service. Also maintains `benchmarks/benchmark.py` and GUI integration as needed. | Why the application uses two indexes, how range searches work, and how performance is measured. |

## Shared/support files

- `src/btree.py` — compatibility facade; imports `BTree` and `BTreeNode` from the teammate-owned algorithm modules.
- `src/models.py` — shared log-record model, timestamp normalization, and validation (including valid IPv4/IPv6 source addresses).
- `src/gui.py` — dark-mode Tkinter interface.
- `src/log_store.py`, `src/index_manager.py`, `src/query_engine.py`, and `src/log_system.py` — small compatibility modules re-exporting the relevant classes from `src/log_indexing.py`, so existing imports continue working.
- `tests/` — regression and automated tests.

## GitHub contribution checklist

1. Each member must use their own GitHub account.
2. Each member should edit and commit genuine changes to their assigned primary file. Add related tests for the code you implement.
3. Use separate branches such as `member-1/btree-core`, `member-2/btree-insertion`, `member-3/btree-deletion`, and `member-4/log-indexing` if that fits your team's workflow.
4. Keep meaningful commit messages and push commits to the shared repository.
5. Every member should understand how their component connects to the whole application.

Do not manufacture commit history or commit on behalf of another teammate. Faculty can inspect the actual changes in each member's commits.
