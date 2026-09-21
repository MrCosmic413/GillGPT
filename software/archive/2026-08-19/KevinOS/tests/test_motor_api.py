from motors.kevin import Kevin


def main():
    kevin = Kevin()

    try:
        print("Kevin motor API loaded.")
        print("1. Head cycle")
        print("2. Tail wag")
        print("3. Mouth pulse")
        print("4. Stop")
        print("5. Exit")

        while True:
            choice = input("Choose: ").strip()

            if choice == "1":
                kevin.head.cycle()

            elif choice == "2":
                kevin.tail.wag(count=2)

            elif choice == "3":
                kevin.mouth.pulse()

            elif choice == "4":
                kevin.stop()

            elif choice == "5":
                break

            else:
                print("Invalid choice.")

    finally:
        kevin.shutdown()


if __name__ == "__main__":
    main()
