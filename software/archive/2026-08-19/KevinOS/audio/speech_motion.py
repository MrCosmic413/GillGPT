import queue
import threading
import time


class SpeechMotion:
    def __init__(self, kevin):
        self.kevin = kevin

        self.events = queue.Queue(maxsize=1)
        self.mouth_events = queue.Queue(maxsize=1)

        self.running = True

        # -------------------------
        # TORSO / HEAD
        # -------------------------
        self.speech_threshold = 0.022
        self.silence_delay = 0.42

        self.speaking = False
        self.last_voice_time = 0.0

        # -------------------------
        # MOUTH
        # -------------------------
        self.mouth_threshold = 0.022

        self.smoothed_amplitude = 0.0
        self.smoothing = 0.35

        self.last_mouth_time = 0.0

        # Lets us alternate between
        # fast and slower mouth actions
        self.mouth_count = 0

        self.torso_worker = threading.Thread(
            target=self._torso_worker,
            daemon=True
        )

        self.mouth_worker = threading.Thread(
            target=self._mouth_worker,
            daemon=True
        )

        self.torso_worker.start()
        self.mouth_worker.start()

    def update(self, amplitude):
        if not self.running:
            return

        # Smooth out sudden audio spikes
        self.smoothed_amplitude = (
            0.65 * self.smoothed_amplitude
            + 0.35 * amplitude
        )

        # -------------------------
        # TORSO AUDIO
        # -------------------------
        try:
            while True:
                self.events.get_nowait()
                self.events.task_done()

        except queue.Empty:
            pass

        try:
            self.events.put_nowait(
                self.smoothed_amplitude
            )

        except queue.Full:
            pass

        # -------------------------
        # MOUTH AUDIO
        # -------------------------
        if (
            self.smoothed_amplitude
            >= self.mouth_threshold
        ):
            try:
                while True:
                    self.mouth_events.get_nowait()
                    self.mouth_events.task_done()

            except queue.Empty:
                pass

            try:
                self.mouth_events.put_nowait(
                    self.smoothed_amplitude
                )

            except queue.Full:
                pass

    # =========================
    # TORSO
    # =========================
    def _torso_worker(self):
        while self.running:
            try:
                amplitude = self.events.get(
                    timeout=0.05
                )

            except queue.Empty:
                self._check_for_silence()
                continue

            try:
                now = time.monotonic()

                if (
                    amplitude
                    >= self.speech_threshold
                ):
                    self.last_voice_time = now

                    if not self.speaking:
                        self.kevin.head.out()
                        self.speaking = True

                else:
                    self._check_for_silence()

            finally:
                self.events.task_done()

    def _check_for_silence(self):
        if not self.speaking:
            return

        if (
            time.monotonic()
            - self.last_voice_time
            >= self.silence_delay
        ):
            self.kevin.head.home()
            self.speaking = False

    # =========================
    # MOUTH
    # =========================
    def _mouth_worker(self):
        while self.running:
            try:
                amplitude = self.mouth_events.get(
                    timeout=0.10
                )

            except queue.Empty:
                continue

            try:
                now = time.monotonic()

                self.mouth_count += 1

                # -------------------------
                # QUIET SPEECH
                #
                # Smaller and slower
                # -------------------------
                if amplitude < 0.040:
                    minimum_gap = 0.18
                    open_time = 0.060
                    close_time = 0.075

                # -------------------------
                # NORMAL SPEECH
                #
                # Mix normal movement with
                # occasional longer opening
                # -------------------------
                elif amplitude < 0.075:

                    if self.mouth_count % 4 == 0:
                        # Longer syllable / vowel
                        minimum_gap = 0.20
                        open_time = 0.125
                        close_time = 0.080

                    else:
                        minimum_gap = 0.135
                        open_time = 0.080
                        close_time = 0.065

                # -------------------------
                # EMPHASIS
                #
                # Faster + stronger
                # -------------------------
                else:

                    if self.mouth_count % 3 == 0:
                        # Strong longer opening
                        minimum_gap = 0.16
                        open_time = 0.135
                        close_time = 0.075

                    else:
                        # Fast syllable movement
                        minimum_gap = 0.105
                        open_time = 0.095
                        close_time = 0.055

                if (
                    now - self.last_mouth_time
                    < minimum_gap
                ):
                    continue

                self.kevin.mouth.pulse(
                    open_time=open_time,
                    close_time=close_time
                )

                self.last_mouth_time = now

            finally:
                self.mouth_events.task_done()

    # =========================
    # SHUTDOWN
    # =========================
    def stop(self):
        self.running = False

        self.torso_worker.join(
            timeout=2.0
        )

        self.mouth_worker.join(
            timeout=2.0
        )

        if self.speaking:
            self.kevin.head.home()

        self.speaking = False
