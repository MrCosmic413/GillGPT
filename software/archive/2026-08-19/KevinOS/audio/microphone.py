import os
import subprocess
import tempfile
import time
import wave

import numpy as np
import requests


class KevinMicrophone:
    def __init__(self):
        # Use the ALSA microphone device that currently works.
        self.device = "plughw:3,0"

        self.stt_url = "http://10.0.0.3:5006/transcribe"

        self.sample_rate = 16000
        self.channels = 1
        self.sample_width = 2

        # 100 ms audio chunks
        self.chunk_seconds = 0.10
        self.chunk_samples = int(
            self.sample_rate * self.chunk_seconds
        )
        self.chunk_bytes = (
            self.chunk_samples * self.sample_width
        )

        # -------------------------
        # SPEECH DETECTION
        # -------------------------
        self.speech_threshold = 0.014

        # Give natural pauses more room.
        self.silence_seconds = 2.0

        # Safety limit for one utterance.
        self.max_record_seconds = 60.0

        # After wake detection, give the microphone
        # a tiny moment before command capture.
        self.wake_delay = 0.15

        # Follow-up conversation window.
        self.followup_timeout = 7.0

    # ==================================================
    # AUDIO HELPERS
    # ==================================================

    def _start_arecord(self):
        return subprocess.Popen(
            [
                "arecord",
                "-q",
                "-D",
                self.device,
                "-t",
                "raw",
                "-f",
                "S16_LE",
                "-r",
                str(self.sample_rate),
                "-c",
                str(self.channels)
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

    def _stop_arecord(self, process):
        process.terminate()

        try:
            process.wait(timeout=1)

        except subprocess.TimeoutExpired:
            process.kill()

    def _rms(self, raw_audio):
        if not raw_audio:
            return 0.0

        samples = np.frombuffer(
            raw_audio,
            dtype=np.int16
        )

        if len(samples) == 0:
            return 0.0

        normalized = (
            samples.astype(np.float32)
            / 32768.0
        )

        return float(
            np.sqrt(
                np.mean(normalized ** 2)
            )
        )

    def _raw_to_wav(self, raw_audio):
        fd, wav_path = tempfile.mkstemp(
            suffix=".wav"
        )

        os.close(fd)

        with wave.open(
            wav_path,
            "wb"
        ) as wav_file:

            wav_file.setnchannels(
                self.channels
            )

            wav_file.setsampwidth(
                self.sample_width
            )

            wav_file.setframerate(
                self.sample_rate
            )

            wav_file.writeframes(
                raw_audio
            )

        return wav_path

    def _transcribe_raw(self, raw_audio):
        wav_path = self._raw_to_wav(
            raw_audio
        )

        try:
            with open(
                wav_path,
                "rb"
            ) as audio_file:

                response = requests.post(
                    self.stt_url,
                    files={
                        "audio": (
                            "kevin_input.wav",
                            audio_file,
                            "audio/wav"
                        )
                    },
                    timeout=60
                )

            response.raise_for_status()

            data = response.json()

            return data.get(
                "text",
                ""
            ).strip()

        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

    # ==================================================
    # WAKE WORD
    # ==================================================

    def wait_for_wake_word(self):
        print(
            '\nKevin is waiting for "Hey Kevin"...'
        )

        process = self._start_arecord()

        wake_chunks = []

        # Analyze about 2.5 seconds at a time.
        target_chunks = int(
            2.5 / self.chunk_seconds
        )

        # Keep one second of overlap.
        overlap_chunks = int(
            1.0 / self.chunk_seconds
        )

        try:
            while True:
                chunk = process.stdout.read(
                    self.chunk_bytes
                )

                if not chunk:
                    continue

                wake_chunks.append(chunk)

                if len(wake_chunks) < target_chunks:
                    continue

                raw_audio = b"".join(
                    wake_chunks
                )

                wake_chunks = wake_chunks[
                    -overlap_chunks:
                ]

                # Don't waste Whisper calls on silence.
                if self._rms(raw_audio) < 0.006:
                    continue

                try:
                    text = self._transcribe_raw(
                        raw_audio
                    )

                except Exception as error:
                    print(
                        f"[WAKE WORD ERROR] {error}"
                    )
                    continue

                if not text:
                    continue

                print(
                    f"[Wake listener heard: {text}]"
                )

                lowered = (
                    text.lower()
                    .replace(",", "")
                    .replace(".", "")
                    .replace("!", "")
                    .replace("?", "")
                    .strip()
                )

                wake_phrases = [
                    "hey kevin",
                    "hey keven",
                    "okay kevin",
                    "ok kevin"
                ]

                wake_detected = any(
                    phrase in lowered
                    for phrase in wake_phrases
                )

                # Whisper may occasionally lose "Hey".
                if (
                    not wake_detected
                    and "kevin" in lowered
                    and len(lowered.split()) <= 4
                ):
                    wake_detected = True

                if wake_detected:
                    print(
                        "\nWake word detected."
                    )

                    return True

        finally:
            self._stop_arecord(
                process
            )

    # ==================================================
    # RECORD ONE UTTERANCE
    # ==================================================

    def _listen_for_speech(
        self,
        start_timeout,
        label="Listening..."
    ):
        print(
            f"\n{label}"
        )

        process = self._start_arecord()

        recorded_chunks = []

        speech_started = False
        silence_time = 0.0

        start_time = time.monotonic()

        try:
            while True:
                chunk = process.stdout.read(
                    self.chunk_bytes
                )

                if not chunk:
                    continue

                amplitude = self._rms(
                    chunk
                )

                elapsed = (
                    time.monotonic()
                    - start_time
                )

                # -------------------------
                # WAIT FOR SPEECH TO BEGIN
                # -------------------------
                if not speech_started:

                    if (
                        amplitude
                        >= self.speech_threshold
                    ):
                        speech_started = True

                        recorded_chunks.append(
                            chunk
                        )

                        print(
                            "Speech detected..."
                        )

                    elif (
                        elapsed
                        >= start_timeout
                    ):
                        return ""

                    continue

                # -------------------------
                # SPEECH HAS STARTED
                # -------------------------
                recorded_chunks.append(
                    chunk
                )

                if (
                    amplitude
                    >= self.speech_threshold
                ):
                    silence_time = 0.0

                else:
                    silence_time += (
                        self.chunk_seconds
                    )

                # Natural end of the utterance.
                if (
                    silence_time
                    >= self.silence_seconds
                ):
                    print(
                        "End of speech detected."
                    )
                    break

                # Safety cap.
                if (
                    elapsed
                    >= self.max_record_seconds
                ):
                    print(
                        "Maximum recording time reached."
                    )
                    break

        finally:
            self._stop_arecord(
                process
            )

        if not recorded_chunks:
            return ""

        raw_audio = b"".join(
            recorded_chunks
        )

        print(
            "Transcribing..."
        )

        return self._transcribe_raw(
            raw_audio
        )

    # ==================================================
    # FIRST COMMAND AFTER WAKE
    # ==================================================

    def listen_after_wake(self):
        time.sleep(
            self.wake_delay
        )

        return self._listen_for_speech(
            start_timeout=8.0,
            label="Listening..."
        )

    # ==================================================
    # FOLLOW-UP LISTENING
    # ==================================================

    def listen_for_followup(
        self,
        timeout=None
    ):
        if timeout is None:
            timeout = self.followup_timeout

        return self._listen_for_speech(
            start_timeout=timeout,
            label="Waiting for a follow-up..."
        )

    # ==================================================
    # ORIGINAL PUBLIC INTERFACE
    # ==================================================

    def listen(self):
        self.wait_for_wake_word()

        return self.listen_after_wake()
