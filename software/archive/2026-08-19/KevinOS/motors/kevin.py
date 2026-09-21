from motors.hardware import KevinController
from motors.head import Head
from motors.mouth import Mouth
from motors.tail import Tail


class Kevin:
    def __init__(self):
        self.hardware = KevinController()

        self.head = Head(self.hardware)
        self.mouth = Mouth(self.hardware)
        self.tail = Tail(self.hardware)

    def stop(self):
        """Immediately stop every motor."""
        self.hardware.stop_all()

    def confirm_home(self):
        """Tell KevinOS that the mechanism is physically at HOME."""
        self.hardware.confirm_home()

    def shutdown(self):
        """Safely stop motors and release GPIO resources."""
        self.hardware.shutdown()
