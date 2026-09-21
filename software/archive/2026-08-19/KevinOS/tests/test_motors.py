from motors.controller import KevinController


def main():
    kevin = KevinController()

    try:
        kevin.interactive_menu()

    finally:
        kevin.shutdown()


if __name__ == "__main__":
    main()
