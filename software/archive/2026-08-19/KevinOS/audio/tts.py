import queue
import requests
import subprocess
import threading
import numpy as np


class KevinTTS:
    def __init__(self, mouth_callback=None):
        self.tts_url = "http://10.0.0.3:5005/speak_raw"
        self.mouth_callback = mouth_callback

        self.speech_queue = queue.Queue()
        self.audio_queue = queue.Queue()

        self.session = requests.Session()

        self.player = subprocess.Popen(
            [
                "aplay",
                "-q",
                "-D",
                "plughw:CARD=Headphones,DEV=0",
                "-t",
                "raw",
                "-f",
                "S16_LE",
                "-r",
                "24000",
                "-c",
                "1"
            ],
            stdin=subprocess.PIPE
        )

        self.synthesis_worker = threading.Thread(
            target=self._synthesis_worker,
            daemon=True
        )

        self.playback_worker = threading.Thread(
            target=self._playback_worker,
            daemon=True
        )

        self.synthesis_worker.start()
        self.playback_worker.start()

    def speak(self, text):
        text = text.strip()

        if text:
            self.speech_queue.put(text)

    def _synthesis_worker(self):
        while True:
            text = self.speech_queue.get()

            if text is None:
                self.speech_queue.task_done()
                self.audio_queue.put(None)
                break

            try:
                response = self.session.post(
                    self.tts_url,
                    json={"text": text},
                    timeout=60
                )

                response.raise_for_status()

                audio = response.content

                if audio:
                    self.audio_queue.put(audio)

            except Exception as error:
                print(
                    f"[TTS SYNTHESIS ERROR] {error}"
                )

            finally:
                self.speech_queue.task_done()

    def _playback_worker(self):
        samples_per_frame = 1200
        bytes_per_sample = 2

        frame_bytes = (
            samples_per_frame
            * bytes_per_sample
        )

        while True:
            audio = self.audio_queue.get()

            if audio is None:
                self.audio_queue.task_done()
                break

            try:
                for start in range(
                    0,
                    len(audio),
                    frame_bytes
                ):
                    chunk = audio[
                        start:start + frame_bytes
                    ]

                    if not chunk:
                        continue

                    pcm = np.frombuffer(
                        chunk,
                        dtype=np.int16
                    )

                    if len(pcm) > 0:
                        normalized = (
                            pcm.astype(np.float32)
                            / 32768.0
                        )

                        rms = float(
                            np.sqrt(
                                np.mean(
                                    normalized ** 2
                                )
                            )
                        )

                        if self.mouth_callback:
                            self.mouth_callback(rms)

                    if self.player.stdin:
                        self.player.stdin.write(chunk)
                        self.player.stdin.flush()

            except Exception as error:
                print(
                    f"[TTS PLAYBACK ERROR] {error}"
                )

            finally:
                self.audio_queue.task_done()

    def wait_until_done(self):
        self.speech_queue.join()
        self.audio_queue.join()

    def shutdown(self):
        self.speech_queue.put(None)

        self.synthesis_worker.join()
        self.playback_worker.join()

        if self.player.stdin:
            self.player.stdin.close()

        self.player.wait()

        self.session.close()
