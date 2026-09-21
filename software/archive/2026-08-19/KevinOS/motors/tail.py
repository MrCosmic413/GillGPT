class Tail:
    def __init__(self, hardware):
        self.hardware = hardware

    def wag_once(self):
        self.hardware.tail_wag_once()

    def wag(self, count=3, pause=0.35):
        self.hardware.tail_wag(
            count=count,
            pause=pause
        )
