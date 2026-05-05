import json
from pathlib import Path

from chord_layer import ChordRing, hash_key
from paxos_layer import PaxosGroup, PaxosReplica

# This layer sits on top of chord + paxos

PAGE_RECORDS = 25
REPLICATION_FACTOR = 3

class DFS:
    def __init__(self, ring: ChordRing):
        self.ring = ring
        self.paxos_groups = {}

    # Metadata key stored in chord
    def _metadata_key(self, filename: str) -> str:
        return f"meta:{filename}"

    # Page key stored in chord
    def _page_key(self, filename: str, page_no: int) -> str:
        return f"page:{filename}:{page_no}"

    # Get R successors for replication
    def _replica_nodes(self, key: str):
        return self.ring.successors(hash_key(key), REPLICATION_FACTOR)

    # Write data to all replicas
    def _write_replicated(self, key: str, value):
        replica_nodes = self._replica_nodes(key)

        for node in replica_nodes:
            node.put(key, value)

        return replica_nodes

    # Read from first available replica
    def _read_replicated(self, key: str):
        for node in self._replica_nodes(key):
            value = node.get(key)
            if value is not None:
                return value

        return None

    def _delete_replicated(self, key: str):
        for node in self._replica_nodes(key):
            node.delete(key)

    # Paxos group per file (metadata consistency)
    def _paxos_group(self, filename: str) -> PaxosGroup:
        if filename not in self.paxos_groups:
            metadata_key = self._metadata_key(filename)
            replica_nodes = self._replica_nodes(metadata_key)

            replicas = [
                PaxosReplica(replica_id=f"node-{node.node_id}")
                for node in replica_nodes
            ]

            self.paxos_groups[filename] = PaxosGroup(
                replicas=replicas,
                leader_id=replicas[0].replica_id
            )

        return self.paxos_groups[filename]

    # Create file metadata
    def touch(self, filename: str):
        metadata = {
            "filename": filename,
            "size_bytes": 0,
            "num_pages": 0,
            "pages": [],
            "version": 1
        }
        # Paxos protects metadata creation
        operation = {
            "op": "create_metadata",
            "filename": filename,
            "version": metadata["version"]
        }

        if self._paxos_group(filename).propose(operation):
            self._write_replicated(self._metadata_key(filename), metadata)

        return metadata

    # Append local file into DFS
    def append_file(self, dfs_filename: str, local_path: str):
        path = Path(local_path)
        text = path.read_text(encoding="utf-8").strip()

        # Split into lines
        records = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                records.append(line)

        metadata = self._read_replicated(self._metadata_key(dfs_filename))

        if metadata is None:
            metadata = self.touch(dfs_filename)

        start_page = metadata["num_pages"]
        new_pages = []

        # Split into pages
        for offset in range(0, len(records), PAGE_RECORDS):
            page_no = start_page + len(new_pages)
            page_records = records[offset:offset + PAGE_RECORDS]
            page_key = self._page_key(dfs_filename, page_no)

            replica_nodes = self._write_replicated(page_key, "\n".join(page_records))

            new_pages.append({
                "page_no": page_no,
                "guid": page_key,
                "replicas": [f"node-{node.node_id}" for node in replica_nodes]
            })

        # Update metadata
        new_metadata = {
            "filename": dfs_filename,
            "size_bytes": metadata["size_bytes"] + len(text.encode("utf-8")),
            "num_pages": metadata["num_pages"] + len(new_pages),
            "pages": metadata["pages"] + new_pages,
            "version": metadata["version"] + 1
        }

        # Paxos protects metadata update
        operation = {
            "op": "metadata_update_after_append",
            "filename": dfs_filename,
            "pages_added": len(new_pages),
            "version": new_metadata["version"]
        }

        if self._paxos_group(dfs_filename).propose(operation):
            self._write_replicated(self._metadata_key(dfs_filename), new_metadata)

        return new_metadata

    def read_file(self, dfs_filename: str) -> str:
    # Get metadata from replicated storage
        metadata = self._read_replicated(self._metadata_key(dfs_filename))

        if metadata is None:
            raise FileNotFoundError(dfs_filename)

        output = []
    # Go through pages in order (important for correct file reconstruction)
        for page in sorted(metadata["pages"], key=lambda p: p["page_no"]):
            page_data = self._read_replicated(page["guid"])

        # Take first available replica
            if page_data is not None:
                output.append(page_data)

    # Combine all page contents into one string
        return "\n".join(output)

    def sort_file(self, input_name: str, output_name: str):
         # Read full file from DFS and split into records
        records = self.read_file(input_name).splitlines()
         # Clean up any empty lines
        records = [record.strip() for record in records if record.strip()]
        # Sort records globally (string sort works because of padded numbers)
        records.sort()

        # Write sorted data to temp file so we can reuse append logic
        temp_path = Path(f"{output_name}.tmp")
        temp_path.write_text("\n".join(records), encoding="utf-8")

         # Create new DFS file and append sorted data
        self.touch(output_name)
        output_metadata = self.append_file(output_name, str(temp_path))

        # Delete temp file after use
        temp_path.unlink(missing_ok=True)

        # Paxos ensures all replicas apply the same sorted metadata update
        operation = {
            "op": "metadata_update_after_sort_file",
            "input": input_name,
            "output": output_name,
            "version": output_metadata["version"]
        }

        # Simulate delayed message case here
        self._paxos_group(output_name).propose(operation, delayed=True)

        return records

    def delete_file(self, dfs_filename: str):
        # Get metadata to know what pages to delete
        metadata = self._read_replicated(self._metadata_key(dfs_filename))

         # File doesn't exist
        if metadata is None:
            return False

        # Paxos protects deletion so all replicas agree
        operation = {
            "op": "metadata_update_after_delete_file",
            "filename": dfs_filename,
            "version": metadata["version"] + 1
        }

        if self._paxos_group(dfs_filename).propose(operation):
            # Delete all pages
            for page in metadata["pages"]:
                self._delete_replicated(page["guid"])

            # Delete metadata itself
            self._delete_replicated(self._metadata_key(dfs_filename))
            return True

        return False

    def verify_sorted(self, dfs_filename: str) -> bool:
        # Read file and clean records
        records = self.read_file(dfs_filename).splitlines()
        records = [record.strip() for record in records if record.strip()]

        # Check if already sorted
        return records == sorted(records)

    def metadata_json(self, filename: str) -> str:
        metadata = self._read_replicated(self._metadata_key(filename))
        return json.dumps(metadata, indent=2)

    def print_replica_locations(self, filename: str):
        # Show which nodes store metadata
        metadata_key = self._metadata_key(filename)
        metadata_nodes = self._replica_nodes(metadata_key)

        print(f"\nMetadata replicas for {filename}:")
        for node in metadata_nodes:
            print(f"  {metadata_key} -> node-{node.node_id} port={node.port}")

        metadata = self._read_replicated(metadata_key)

        # Show where each page is replicated
        if metadata:
            print(f"\nPage replicas for {filename}:")
            for page in metadata["pages"]:
                print(f"  {page['guid']} -> {page['replicas']}")
