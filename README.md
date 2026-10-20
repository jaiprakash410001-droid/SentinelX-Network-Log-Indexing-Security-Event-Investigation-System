# Network Log Indexing and Security Event Investigation Engine Using B-Tree

A Python-based DSA project that uses a **B-Tree** to index computer or network log records. The application helps users search for events, retrieve logs within a time range, filter results, and compare B-Tree searching with linear search.

**Course:** Data Structures and Algorithms (DSA)  
**Language:** Python  
**Team size:** 4 members

## What Is the Project?

Computers, servers, and applications create log records when events happen, such as successful logins, failed login attempts, connection errors, or application crashes. Finding a particular event can be slow if the system checks every record one by one.

Our project uses a **B-Tree index** to organize log records by fields such as event ID and timestamp. Users can search for events, find logs within a time range, and filter the results. We will also compare B-Tree search performance with linear search.

The first version uses CSV files or generated sample logs. Live monitoring is optional and is not required for the core project.

## Main Features

- Load log records from a CSV file or use generated sample data.
- Create B-Tree indexes for event IDs and timestamps.
- Search for an event by ID.
- Find events between two timestamps.
- Filter results by severity or source IP address.
- Implement B-Tree insertion, searching, deletion, splitting, borrowing, and merging.
- Display matching records in chronological order.
- Compare B-Tree searching with linear search.

## How It Works

1. Load the log records.
2. Store the records and build B-Tree indexes.
3. Use the relevant index to find event records.
4. Filter and display the matching logs.
5. Test the B-Tree and compare its performance with linear search.

Example records:

| Event ID | Timestamp | Source IP | Severity | Event |
|---|---|---|---|---|
| 101 | 09:00:01 | 192.168.1.5 | INFO | Successful login |
| 102 | 09:02:15 | 192.168.1.8 | HIGH | Failed login |
| 103 | 09:03:10 | 192.168.1.8 | HIGH | Failed login |

For example, a user can request all events between 09:00 and 09:05. The timestamp index helps locate the records in that interval. Repeated failed logins can be highlighted for investigation, but this alone does not prove that an attack occurred.

## Why Use a B-Tree?

A B-Tree is a balanced search tree where each node can contain multiple keys. It keeps keys ordered and supports efficient searching and updates as records are added or removed.

For a B-Tree with a fixed minimum degree:

- **Search:** `O(log n)`
- **Insertion:** `O(log n)`
- **Deletion:** `O(log n)`
- **Full traversal:** `O(n)`
- **Range query returning `k` records:** typically `O(log n + k)` with suitable ordered traversal

Here, `n` is the number of indexed keys and `k` is the number of returned records.

## Team Members and Responsibilities

There are **four separate team-member roles**. Replace each numbered name and roll-number placeholder with the correct details.

### Member 1 — B-Tree Structure, Searching, and Traversal
- Design the B-Tree node structure.
- Implement searching and in-order traversal.
- Check B-Tree properties and calculate tree height.

**Name:** `Dhiraj`  
**Roll number:** `CB.SC.U4CSE25334`

### Member 2 — Insertion and Node Splitting
- Implement key insertion.
- Handle full nodes and split them when required.
- Promote median keys and handle root splitting.

**Name:** `Gokul Akash`  
**Roll number:** `CB.SC.U4CSE25310`

### Member 3 — Deletion and Rebalancing
- Implement key deletion.
- Handle borrowing keys from siblings and merging nodes.
- Handle root adjustment and preserve B-Tree properties.

**Name:** `Divyendrhaa Muthusamy`  
**Roll number:** `CB.SC.U4CSE25318`

### Member 4 — Log Indexing, Range Queries, and Performance Testing
- Load log records from CSV files.
- Connect log records to the event-ID and timestamp indexes.
- Implement time-range queries and result filtering.
- Compare B-Tree searches with linear searches and report measured results.

**Name:** `Jai Prakash`  
**Roll number:** `CB.SC.U4CSE25325`

## Suggested Project Structure

This is a suggested layout; update it to match the actual files in the repository.

```text
network-log-indexing-engine/
├── src/
│   ├── btree.py
│   ├── log_store.py
│   ├── index_manager.py
│   ├── query_engine.py
│   └── main.py
├── data/
│   └── sample_logs.csv
├── tests/
│   └── test_btree.py
├── benchmarks/
│   └── benchmark.py
└── README.md
```

## How to Run

**Requirement:** Python 3.10 or later, depending on the version used by the project.

```bash
git clone https://github.com/<your-username>/<your-repository>.git
cd <your-repository>
python src/main.py
```

Adjust the commands to match the actual repository and entry-point file.

## Testing and Performance Comparison

Test insertion, searching, and deletion with different key sequences. Check that the B-Tree remains valid after splitting, borrowing, and merging. Then compare B-Tree search with linear search using the same datasets.

| Number of records | B-Tree search time | Linear search time |
|---:|---|---|
| 1,000 | To be measured | To be measured |
| 10,000 | To be measured | To be measured |
| 100,000 | To be measured | To be measured |

Fill in the table with actual measurements after running the program.

## Future Improvements

- Add a graphical view of the B-Tree.
- Animate splitting, borrowing, and merging.
- Add more log filters and investigation rules.
- Add live log input as an optional extension.

## References

- Cormen, Leiserson, Rivest, and Stein, *Introduction to Algorithms* — B-Trees.
- Bayer, R. and McCreight, E. (1972), *Organization and Maintenance of Large Ordered Indexes*.
- Python CSV documentation: https://docs.python.org/3/library/csv.html

---

**Project summary:** This project demonstrates how a B-Tree can make searching and retrieving records from large log datasets more efficient. It combines B-Tree algorithms with a practical log-investigation example and performance testing.
