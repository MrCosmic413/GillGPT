from enum import Enum, auto
from gpiozero import OutputDevice, PWMOutputDevice
from time import sleep


class KevinState(Enum):
    HOME = auto()
    HEAD_OUT = auto()
    UNKNOWN = auto()


class KevinController:
    # =========================================================
    # CALIBRATED VALUES
    # =========================================================

    BODY_SPEED = 0.75
    MOUTH_SPEED = 0.80

    TAIL_OUT_TIME = 0.55
    TAIL_RESET_TIME = 0.30
    TAIL_SPRING_WAIT = 0.15

    HEAD_OUT_TIME = 0.70

    # Two-stage head return
    HEAD_HOME_MAIN_TIME = 0.46
    HEAD_HOME_MAIN_SPEED = 0.75
    HEAD_HOME_SETTLE_WAIT = 0.10
    HEAD_HOME_FINAL_TIME = 0.04
    HEAD_HOME_FINAL_SPEED = 0.45

    def __init__(self):
        # =====================================================
        # MOTOR A: MOUTH
        # =====================================================

        self.ain1 = OutputDevice(17)
        self.ain2 = OutputDevice(27)
        self.pwma = PWMOutputDevice(18)

        # =====================================================
        # MOTOR B: SHARED HEAD / TAIL MECHANISM
        # =====================================================

        self.bin1 = OutputDevice(22)
        self.bin2 = OutputDevice(23)
        self.pwmb = PWMOutputDevice(19)

        # Motor-driver standby
        self.stby = OutputDevice(24)

        self.stby.on()
        self.stop_all()

        # Kevin must begin manually positioned at equilibrium.
        self.state = KevinState.HOME

        print("Kevin initialized at HOME.")

    # =========================================================
    # LOW-LEVEL MOUTH CONTROL
    # =========================================================

    def _mouth_open_direction(self, speed=None):
        if speed is None:
            speed = self.MOUTH_SPEED

        self.pwma.value = speed
        self.ain1.on()
        self.ain2.off()

    def _mouth_close_direction(self, speed=None):
        if speed is None:
            speed = self.MOUTH_SPEED

        self.pwma.value = speed
        self.ain1.off()
        self.ain2.on()

    def mouth_stop(self):
        self.ain1.off()
        self.ain2.off()
        self.pwma.value = 0

    # =========================================================
    # LOW-LEVEL HEAD / TAIL MOTOR CONTROL
    # =========================================================

    def _electrical_out(self, speed=None):
        """
        Electrical OUT direction.

        From HOME:
        - moves the tail outward

        From HEAD_OUT:
        - returns the head toward HOME
        """

        if speed is None:
            speed = self.BODY_SPEED

        self.pwmb.value = speed
        self.bin1.on()
        self.bin2.off()

    def _electrical_in(self, speed=None):
        """
        Electrical IN direction.

        From HOME:
        - moves the head outward

        After a tail movement:
        - resets the internal mechanism
        """

        if speed is None:
            speed = self.BODY_SPEED

        self.pwmb.value = speed
        self.bin1.off()
        self.bin2.on()

    def body_stop(self):
        self.bin1.off()
        self.bin2.off()
        self.pwmb.value = 0

    def stop_all(self):
        self.mouth_stop()
        self.body_stop()

    # =========================================================
    # MOUTH MOVEMENTS
    # =========================================================

    def open_mouth(self, duration=0.15, speed=None):
        self._mouth_open_direction(speed)
        sleep(duration)
        self.mouth_stop()

    def close_mouth(self, duration=0.12, speed=None):
        self._mouth_close_direction(speed)
        sleep(duration)
        self.mouth_stop()

    def mouth_pulse(
        self,
        open_time=0.15,
        close_time=0.12,
        speed=None
    ):
        self._mouth_open_direction(speed)
        sleep(open_time)

        self._mouth_close_direction(speed)
        sleep(close_time)

        self.mouth_stop()

    def talking_motion(
        self,
        seconds=2.0,
        open_time=0.14,
        close_time=0.11,
        speed=None
    ):
        cycle_time = open_time + close_time
        cycle_count = max(1, int(seconds / cycle_time))

        for _ in range(cycle_count):
            self._mouth_open_direction(speed)
            sleep(open_time)

            self._mouth_close_direction(speed)
            sleep(close_time)

        self.mouth_stop()

    # =========================================================
    # STATE CONTROL
    # =========================================================

    def confirm_home(self):
        """
        Use only after manually positioning Kevin flat,
        with the tail centered and mouth closed.
        """

        self.stop_all()
        self.state = KevinState.HOME
        print("Kevin manually confirmed at HOME.")

    def mark_unknown(self):
        self.stop_all()
        self.state = KevinState.UNKNOWN
        print("Kevin's position is now UNKNOWN.")

    # =========================================================
    # CALIBRATED HEAD MOVEMENTS
    # =========================================================

    def head_out(self):
        """
        HOME -> HEAD_OUT

        Electrical IN for 0.50 seconds.
        """

        if self.state == KevinState.HEAD_OUT:
            print("Kevin's head is already out.")
            return

        if self.state != KevinState.HOME:
            print("Head movement cancelled: Kevin is not confirmed HOME.")
            return

        print("Moving Kevin's head outward...")

        self._electrical_in()
        sleep(self.HEAD_OUT_TIME)
        self.body_stop()

        self.state = KevinState.HEAD_OUT

    def head_home(self):
        """
        HEAD_OUT -> HOME

        Uses a two-stage return to reduce accidental
        tail engagement and tail jitter.
        """

        if self.state == KevinState.HOME:
            print("Kevin is already HOME.")
            return

        if self.state != KevinState.HEAD_OUT:
            print("Head-home movement cancelled: state is unknown.")
            return

        print("Returning Kevin's head HOME...")

        # Main return movement
        self._electrical_out(
            speed=self.HEAD_HOME_MAIN_SPEED
        )
        sleep(self.HEAD_HOME_MAIN_TIME)
        self.body_stop()

        # Let the spring and linkage settle
        sleep(self.HEAD_HOME_SETTLE_WAIT)

        # Gentle final positioning pulse
        self._electrical_out(
            speed=self.HEAD_HOME_FINAL_SPEED
        )
        sleep(self.HEAD_HOME_FINAL_TIME)
        self.body_stop()

        self.state = KevinState.HOME

    def head_cycle(self, pause=0.40):
        """
        HOME -> HEAD_OUT -> HOME
        """

        if self.state != KevinState.HOME:
            print("Head cycle cancelled: Kevin is not HOME.")
            return

        self.head_out()
        sleep(pause)
        self.head_home()

    # =========================================================
    # CALIBRATED TAIL MOVEMENTS
    # =========================================================

    def tail_wag_once(self):
        """
        Starting from HOME:

        1. Electrical OUT for 0.35 seconds.
        2. Stop and allow the spring to return the visible tail.
        3. Electrical IN for 0.20 seconds to reset the mechanism.
        """

        if self.state != KevinState.HOME:
            print("Tail wag cancelled: Kevin must be HOME.")
            return

        print("Moving Kevin's tail...")

        self._electrical_out()
        sleep(self.TAIL_OUT_TIME)
        self.body_stop()

        sleep(self.TAIL_SPRING_WAIT)

        print("Resetting tail mechanism...")

        self._electrical_in()
        sleep(self.TAIL_RESET_TIME)
        self.body_stop()

        self.state = KevinState.HOME

    def tail_wag(self, count=3, pause=0.35):
        """
        Repeat the calibrated tail cycle.
        """

        if self.state != KevinState.HOME:
            print("Tail sequence cancelled: Kevin must be HOME.")
            return

        for wag_number in range(1, count + 1):
            print(f"Tail wag {wag_number} of {count}")
            self.tail_wag_once()
            sleep(pause)

    # =========================================================
    # SCRIPTED BEHAVIORS
    # =========================================================

    def greeting(self):
        """
        HOME -> head out -> talking -> HOME
        """

        print("\nRunning greeting...")

        if self.state != KevinState.HOME:
            print("Greeting cancelled: Kevin must start at HOME.")
            return

        self.head_out()
        sleep(0.20)

        self.talking_motion(
            seconds=2.0,
            open_time=0.14,
            close_time=0.11,
            speed=0.80
        )

        sleep(0.20)
        self.head_home()

        self.stop_all()

    def calm_talking(self, seconds=4.0):
        """
        HOME -> head out -> slower talking -> HOME
        """

        print("\nRunning calm talking...")

        if self.state != KevinState.HOME:
            print("Calm talking cancelled: Kevin must start at HOME.")
            return

        self.head_out()
        sleep(0.20)

        self.talking_motion(
            seconds=seconds,
            open_time=0.18,
            close_time=0.15,
            speed=0.65
        )

        sleep(0.20)
        self.head_home()

        self.stop_all()

    def surprised_reaction(self):
        """
        HOME -> head out -> mouth opens
        -> rapid talking -> HOME
        """

        print("\nRunning surprised reaction...")

        if self.state != KevinState.HOME:
            print("Surprised reaction cancelled: Kevin must start at HOME.")
            return

        self.head_out()

        self._mouth_open_direction(0.90)
        sleep(0.35)
        self.mouth_stop()

        sleep(0.10)

        self.talking_motion(
            seconds=1.25,
            open_time=0.09,
            close_time=0.08,
            speed=0.90
        )

        self.head_home()
        self.stop_all()

    def happy_tail(self):
        """
        Tail-only happy reaction.
        """

        print("\nRunning happy-tail reaction...")

        if self.state != KevinState.HOME:
            print("Happy-tail reaction cancelled: Kevin must be HOME.")
            return

        self.tail_wag(
            count=3,
            pause=0.30
        )

        self.stop_all()

    def excited_reaction(self):
        """
        Head movement first, then HOME, then tail movement.

        The head and tail are never commanded at the same time.
        """

        print("\nRunning excited reaction...")

        if self.state != KevinState.HOME:
            print("Excited reaction cancelled: Kevin must start at HOME.")
            return

        self.head_out()

        self.talking_motion(
            seconds=1.5,
            open_time=0.10,
            close_time=0.08,
            speed=0.90
        )

        self.head_home()
        sleep(0.30)

        self.tail_wag(
            count=3,
            pause=0.25
        )

        self.stop_all()

    def full_performance(self):
        """
        Runs only calibrated transitions.
        """

        print("\nStarting Kevin's full performance...")

        if self.state != KevinState.HOME:
            print("Performance cancelled: Kevin must begin at HOME.")
            return

        self.greeting()
        sleep(0.75)

        self.happy_tail()
        sleep(0.75)

        self.surprised_reaction()
        sleep(0.75)

        self.excited_reaction()

        self.stop_all()

        print("Performance complete.")
        print(f"Software state: {self.state.name}")

    # =========================================================
    # INTERACTIVE MENU
    # =========================================================

    def interactive_menu(self):
        while True:
            print("\nKevin Movement Menu")
            print("-------------------")
            print(f"Current state: {self.state.name}")
            print()
            print("1  - Greeting")
            print("2  - Calm talking")
            print("3  - Surprised reaction")
            print("4  - Happy tail")
            print("5  - Excited reaction")
            print("6  - Full performance")
            print("7  - Head out")
            print("8  - Head home")
            print("9  - Full head cycle")
            print("10 - Tail wag once")
            print("11 - Tail wag three times")
            print("12 - Mouth pulse")
            print("h  - Confirm manually positioned HOME")
            print("s  - Emergency stop and mark UNKNOWN")
            print("q  - Quit")

            choice = input("\nChoose an option: ").strip().lower()

            if choice == "1":
                self.greeting()

            elif choice == "2":
                self.calm_talking()

            elif choice == "3":
                self.surprised_reaction()

            elif choice == "4":
                self.happy_tail()

            elif choice == "5":
                self.excited_reaction()

            elif choice == "6":
                self.full_performance()

            elif choice == "7":
                self.head_out()

            elif choice == "8":
                self.head_home()

            elif choice == "9":
                self.head_cycle()

            elif choice == "10":
                self.tail_wag_once()

            elif choice == "11":
                self.tail_wag(count=3)

            elif choice == "12":
                self.mouth_pulse()

            elif choice == "h":
                confirmation = input(
                    "Is Kevin flat, tail centered, and mouth closed? "
                    "Type yes: "
                ).strip().lower()

                if confirmation == "yes":
                    self.confirm_home()
                else:
                    print("HOME was not confirmed.")

            elif choice == "s":
                self.mark_unknown()
                print(
                    "Manually return Kevin to equilibrium "
                    "before continuing."
                )

            elif choice == "q":
                print("Exiting Kevin movement control.")
                break

            else:
                print("Invalid option.")

            self.stop_all()

    # =========================================================
    # SHUTDOWN
    # =========================================================

    def shutdown(self):
        self.stop_all()
        self.stby.off()
        print("Motor driver disabled safely.")


if __name__ == "__main__":
    kevin = KevinController()

    try:
        kevin.interactive_menu()

    except KeyboardInterrupt:
        print("\nProgram interrupted.")
        kevin.mark_unknown()

    finally:
        kevin.shutdown()
