from chord_layer import ChordRing

def main():
    ring = ChordRing()

    print("This project uses a repeatable single-process simulation.")
    print("For the full assignment demo, run:")
    print("python demo.py")

    print("\nCreating 5 local Chord peers:")

    for port in [8000, 8001, 8002, 8003, 8004]:
        ring.add_node(port)

    ring.print_ring()
    ring.print_finger_tables()

if __name__ == "__main__":
    main()
