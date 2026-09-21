class Mouth:
    def __init__(self, hardware):
        self.hardware = hardware

    def open(self, duration=0.15, speed=None):
        self.hardware.open_mouth(
            duration=duration,
            speed=speed
        )

    def close(self, duration=0.12, speed=None):
        self.hardware.close_mouth(
            duration=duration,
            speed=speed
        )

    def pulse(
        self,
        open_time=0.15,
        close_time=0.12,
        speed=None
    ):
        self.hardware.mouth_pulse(
            open_time=open_time,
            close_time=close_time,
            speed=speed
        )

    def stop(self):
        self.hardware.mouth_stop()
