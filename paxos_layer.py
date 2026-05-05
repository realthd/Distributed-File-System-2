from dataclasses import dataclass, field

# Represents one replica in the Paxos group
@dataclass
class PaxosReplica:
    replica_id: str
    alive: bool = True
    learned_log: list = field(default_factory=list)

    # Receive ACCEPT and respond with LEARN (if alive)
    def accept(self, operation: dict, ballot: int):
        if not self.alive:
            return None

        return {
            "type": "LEARN",
            "replica": self.replica_id,
            "ballot": ballot,
            "operation": operation
        }

    # Apply committed operation
    def apply(self, operation: dict):
        if self.alive:
            self.learned_log.append(operation)

class PaxosGroup:
    def __init__(self, replicas: list[PaxosReplica], leader_id: str):
        self.replicas = replicas
        self.leader_id = leader_id
        self.ballot = 0
        self.committed_log = []

    # Majority = floor(n/2) + 1
    def majority(self) -> int:
        return len(self.replicas) // 2 + 1

    # Propose an operation (simplified Paxos)
    def propose(self, operation: dict, simulate_crash: str | None = None, delayed: bool = False) -> bool:
        self.ballot += 1
        ballot = self.ballot

        print(f"\nPAXOS leader={self.leader_id} ballot={ballot}")
        print(f"ACCEPT(o={operation}, t={ballot})")

        # Simulate failure before responses
        if simulate_crash:
            for replica in self.replicas:
                if replica.replica_id == simulate_crash:
                    replica.alive = False
                    print(f"FAILURE: replica {replica.replica_id} crashed before responding")

        learns = []
        delayed_msg = None

        for replica in self.replicas:
            msg = replica.accept(operation, ballot)

            if msg is None:
                continue
            # Simulate delayed message
            if delayed and delayed_msg is None:
                delayed_msg = msg
                print(f"DELAYED: LEARN from {replica.replica_id}")
                continue

            learns.append(msg)
            print(f"LEARN(o={operation}, t={ballot}) from {replica.replica_id}")
        
        # Simulate retransmission if needed
        if len(learns) < self.majority() and delayed_msg:
            print("TIMEOUT: retransmitting ACCEPT")
            learns.append(delayed_msg)
            print(f"LEARN(o={operation}, t={ballot}) from {delayed_msg['replica']} after retransmission")

        committed = len(learns) >= self.majority()

        print(
            f"COMMIT decision={committed} "
            f"learned={len(learns)}/{len(self.replicas)} "
            f"majority={self.majority()}"
        )

        # Apply operation if committed
        if committed:
            self.committed_log.append(operation)
            for replica in self.replicas:
                replica.apply(operation)

        return committed
