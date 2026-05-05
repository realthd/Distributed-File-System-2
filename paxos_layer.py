from dataclasses import dataclass, field

@dataclass
class PaxosReplica:
    replica_id: str
    alive: bool = True
    learned_log: list = field(default_factory=list)

    def accept(self, operation: dict, ballot: int):
        if not self.alive:
            return None

        return {
            "type": "LEARN",
            "replica": self.replica_id,
            "ballot": ballot,
            "operation": operation
        }

    def apply(self, operation: dict):
        if self.alive:
            self.learned_log.append(operation)

class PaxosGroup:
    def __init__(self, replicas: list[PaxosReplica], leader_id: str):
        self.replicas = replicas
        self.leader_id = leader_id
        self.ballot = 0
        self.committed_log = []

    def majority(self) -> int:
        return len(self.replicas) // 2 + 1

    def propose(self, operation: dict, simulate_crash: str | None = None, delayed: bool = False) -> bool:
        self.ballot += 1
        ballot = self.ballot

        print(f"\nPAXOS leader={self.leader_id} ballot={ballot}")
        print(f"ACCEPT(o={operation}, t={ballot})")

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

            if delayed and delayed_msg is None:
                delayed_msg = msg
                print(f"DELAYED: LEARN from {replica.replica_id}")
                continue

            learns.append(msg)
            print(f"LEARN(o={operation}, t={ballot}) from {replica.replica_id}")

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

        if committed:
            self.committed_log.append(operation)
            for replica in self.replicas:
                replica.apply(operation)

        return committed
