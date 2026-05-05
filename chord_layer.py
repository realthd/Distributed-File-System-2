import hashlib
from dataclasses import dataclass, field

# Size of identifier space (2^8 = 256)
M = 8
RING_SIZE = 2 ** M

# Hash a string into the ring space
def hash_key(value: str) -> int:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
    return int(digest, 16) % RING_SIZE

@dataclass
class ChordNode:
    node_id: int
    port: int
    storage: dict = field(default_factory=dict)
    finger_table: list = field(default_factory=list)

    # Store key locally
    def put(self, key: str, value):
        self.storage[key] = value
    # Retrieve key if it exists
    def get(self, key: str):
        return self.storage.get(key)
    # Remove key if it exists
    def delete(self, key: str):
        self.storage.pop(key, None)

class ChordRing:
    def __init__(self, m: int = M):
        self.m = m
        self.ring_size = 2 ** m
        self.nodes = []

    # Add a new node into ring
    def add_node(self, port: int) -> ChordNode:
        node_id = hash_key(str(port))

        while any(n.node_id == node_id for n in self.nodes):
            node_id = (node_id + 1) % self.ring_size

        node = ChordNode(node_id=node_id, port=port)
        self.nodes.append(node)
        self.nodes.sort(key=lambda n: n.node_id)

        # Rebuild finger tables whenever topology changes
        self.rebuild_fingers()
        return node

    # Find successor responsible for a key
    def locate_successor(self, key_or_id) -> ChordNode:
        key_id = key_or_id if isinstance(key_or_id, int) else hash_key(str(key_or_id))

        for node in self.nodes:
            if node.node_id >= key_id:
                return node

        # Wrap around case
        return self.nodes[0]

    # Return next R successors (used for replication)
    def successors(self, key_or_id, count: int = 3):
        first = self.locate_successor(key_or_id)
        start = self.nodes.index(first)
        return [self.nodes[(start + i) % len(self.nodes)] for i in range(count)]

    # Build finger table for faster lookup
    def rebuild_fingers(self):
        for node in self.nodes:
            node.finger_table = []

            for i in range(self.m):
                start = (node.node_id + 2 ** i) % self.ring_size
                succ = self.locate_successor(start)
                node.finger_table.append((i, start, succ.node_id, succ.port))

    # Helpers for demo
    def print_ring(self):
        print("\nCHORD RING")
        for node in self.nodes:
            print(f"Node {node.node_id:3d} on port {node.port}")

    def print_finger_tables(self):
        print("\nFINGER TABLES")
        for node in self.nodes:
            print(f"\nNode {node.node_id} port={node.port}")
            for i, start, succ, port in node.finger_table:
                print(f"  finger[{i}] start={start:3d} -> node={succ:3d} port={port}")
