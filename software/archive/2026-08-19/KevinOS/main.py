from ai.brain import KevinBrain
from ai.command_router import CommandRouter
from ai.file_commands import FileCommands
from ai.spotify_commands import SpotifyCommands

from audio.microphone import KevinMicrophone
from audio.speech_motion import SpeechMotion
from audio.tts import KevinTTS

from motors.kevin import Kevin


def main():
    brain = KevinBrain()

    spotify = SpotifyCommands()
    files = FileCommands()

    router = CommandRouter(
        brain=brain,
        spotify=spotify,
        files=files
    )

    kevin = Kevin()
    microphone = KevinMicrophone()

    speech_motion = SpeechMotion(
        kevin
    )

    tts = KevinTTS(
        mouth_callback=speech_motion.update
    )

    print("\nKevinOS started.")
    print('Say "Hey Kevin" to wake Kevin.')
    print("Press Ctrl+C to stop.")

    def speak_message(message):
        print(
            f"\nKevin: {message}"
        )

        tts.speak(message)
        tts.wait_until_done()

    def handle_input(text):
        if not text:
            return

        print(
            f"\nYou: {text}"
        )

        result = router.route(text)

        if result:
            speak_message(
                result["message"]
            )

            return

        brain.handle_text_stream(
            text,
            sentence_callback=tts.speak
        )

        tts.wait_until_done()

    try:
        while True:

            # =============================
            # WAKE MODE
            # =============================

            microphone.wait_for_wake_word()

            print(
                "\nKevin is awake."
            )
            # Quick physical acknowledgment:
            # "I heard you."
            kevin.mouth.pulse(
                open_time=0.07,
                close_time=0.06
            )

            # =============================
            # FIRST COMMAND
            # =============================

            text = (
                microphone
                .listen_after_wake()
            )

            if not text:
                print(
                    "No command heard."
                )
                continue

            handle_input(text)

            # =============================
            # ACTIVE CONVERSATION
            # =============================

            while True:
                followup = (
                    microphone
                    .listen_for_followup(
                        timeout=8.0
                    )
                )

                if not followup:
                    print(
                        "\nConversation ended."
                    )

                    break

                handle_input(
                    followup
                )

    except KeyboardInterrupt:
        print(
            "\nStopping KevinOS..."
        )

    finally:
        print(
            "Shutting Kevin down safely..."
        )

        tts.wait_until_done()

        speech_motion.stop()

        tts.shutdown()

        kevin.shutdown()

        print(
            "KevinOS stopped."
        )


if __name__ == "__main__":
    main()
