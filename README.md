# Distributed-File-System-2

## How to Run the System

1. Make sure you have Python 3 installed (tested on Python 3.10+)

2. From the project directory, run:

```bash
python demo.py
```

This will automatically:

* create the Chord ring
* run DFS operations
* run sorting demo
* run Paxos + failure demo

---

## How to Start Peers

This project uses a **single-process simulation** of multiple peers.

When you run:

```bash
python demo.py
```

it creates 5 Chord nodes on these ports:

```
8000, 8001, 8002, 8003, 8004
```

Each node is assigned:

* a hashed node ID
* a finger table
* local storage

You can see all nodes and their finger tables printed at startup.

---

## How to Issue DFS Commands

DFS functionality is implemented in `dfs_layer.py`.

Main operations:

### Create a file

```python
dfs.touch("filename")
```

### Append local file data

```python
dfs.append_file("filename", "path/to/local_file.txt")
```

### Read a file

```python
dfs.read_file("filename")
```

### Delete a file

```python
dfs.delete_file("filename")
```

### Sort a file

```python
dfs.sort_file("input_file", "output_file")
```

These commands are already demonstrated in `demo.py`.

---

## How to Run the Sorting Demo

The sorting demo is executed automatically in `demo.py`.

Steps performed:

1. Creates a file with 130 records:

```text
big.csv
```

2. Calls:

```python
dfs.sort_file("big.csv", "big_sorted.csv")
```

3. Writes result to:

```
sorted_output.csv
```

4. Verifies correctness:

```text
Globally sorted: True
```

The program also prints:

* first 10 sorted records
* last 10 sorted records

---

## How to Run the Paxos Demo

Paxos is used to coordinate **replicated metadata updates**.

The demo automatically shows:

### 1. Normal operation

For each DFS update:

* leader sends ACCEPT
* replicas respond with LEARN
* majority commits

Example output:

```
PAXOS leader=node-210 ballot=2
ACCEPT(...)
LEARN from node-210
LEARN from node-234
COMMIT decision=True
```

---

### 2. Delayed message case (sorting)

During sorting:

* one LEARN message is delayed
* system still commits using majority

---

### 3. Failure case (replica crash)

The demo simulates:

* one replica crashing before responding

Example:

```
FAILURE: replica node-53 crashed
```

System still commits because:

* 2 out of 3 replicas form a majority

---

### 4. Delete operation (Paxos-protected)

```python
dfs.delete_file("music.csv")
```

This triggers:

* Paxos agreement
* replicated metadata deletion
* page cleanup

---

## Summary

This system demonstrates:

* Chord-based distributed storage
* Page-based file system design
* Replication (R = 3)
* Paxos-based consistency
* Distributed sorting
* Fault tolerance under node failure
