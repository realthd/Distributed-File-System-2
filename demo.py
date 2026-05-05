from pathlib import Path

from chord_layer import ChordRing
from dfs_layer import DFS

def make_samples():
    Path("samples").mkdir(exist_ok=True)

    Path("samples/a.txt").write_text(
        "0042,bob\n0012,alice\n0190,carol\n",
        encoding="utf-8"
    )

    Path("samples/b.txt").write_text(
        "0008,dana\n0133,eric\n0060,faye\n",
        encoding="utf-8"
    )

    Path("samples/c.txt").write_text(
        "0100,gina\n0001,hank\n0177,ivan\n",
        encoding="utf-8"
    )

    records = []

    for i in range(130, 0, -1):
        records.append(f"{i:04d},record_{i}")

    Path("samples/unsorted_130.txt").write_text(
        "\n".join(records),
        encoding="utf-8"
    )

def main():
    make_samples()

    ring = ChordRing()

    for port in [8000, 8001, 8002, 8003, 8004]:
        ring.add_node(port)

    ring.print_ring()
    ring.print_finger_tables()

    dfs = DFS(ring)

    print("\nDFS CREATE + APPEND DEMO")

    dfs.touch("music.csv")
    dfs.append_file("music.csv", "samples/a.txt")
    dfs.append_file("music.csv", "samples/b.txt")
    dfs.append_file("music.csv", "samples/c.txt")

    print("\nMetadata JSON:")
    print(dfs.metadata_json("music.csv"))

    dfs.print_replica_locations("music.csv")

    print("\nRead back from DFS:")
    print(dfs.read_file("music.csv"))

    print("\nSORTING DEMO: 130 RECORDS")

    dfs.touch("big.csv")
    dfs.append_file("big.csv", "samples/unsorted_130.txt")

    sorted_records = dfs.sort_file("big.csv", "big_sorted.csv")

    Path("sorted_output.csv").write_text(
        "\n".join(sorted_records),
        encoding="utf-8"
    )

    print("Sorted output written to sorted_output.csv")
    print("Globally sorted:", dfs.verify_sorted("big_sorted.csv"))

    print("\nFirst 10 sorted records:")
    for record in sorted_records[:10]:
        print(record)

    print("\nLast 10 sorted records:")
    for record in sorted_records[-10:]:
        print(record)

    print("\nFAILURE DEMO")

    group = dfs._paxos_group("music.csv")
    crashed_replica = group.replicas[-1].replica_id

    group.propose(
        {
            "op": "metadata_update_after_append",
            "filename": "music.csv",
            "version": 99
        },
        simulate_crash=crashed_replica
    )

    print("\nDELETE FILE DEMO")

    deleted = dfs.delete_file("music.csv")
    print("Deleted music.csv:", deleted)

if __name__ == "__main__":
    main()
