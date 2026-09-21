class Head:
    def __init__(self, hardware):
        self.hardware = hardware

    def out(self):
        self.hardware.head_out()

    def home(self):
        self.hardware.head_home()

    def cycle(self, pause=0.40):
        self.hardware.head_cycle(pause=pause)
