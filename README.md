# GillGPT — Meet Kevin 🐟

Kevin is an AI-powered animatronic fish built by modifying a Big Mouth Billy Bass. GillGPT brings together conversational AI, speech recognition, synthesized speech, a Raspberry Pi, FPGA motor control, and a custom KiCad PCB.

The project has grown from reverse-engineering two motors into an integrated hardware/software build: Kevin speaks, moves his mouth with the audio, and shows activity on an LCD.

## How it works

```text
Microphone → Raspberry Pi / KevinOS → PC speech recognition
                        ↓
                   Ollama response
                        ↓
                  Kokoro speech → Speaker
                        ↓
              Mouth animation + LCD feedback
                        ↓
       UART → Tang Nano 9K FPGA → TB6612FNG → Motors
```

The Raspberry Pi coordinates the interaction. The PC provides AI and speech services. The Tang Nano 9K handles timed motor sequences in Verilog, with the TB6612FNG driving the mouth and shared head/tail mechanism.

## Build status — September 20, 2026

- Original mechanism reverse engineered; motor direction and wiring documented.
- Custom KiCad schematic, PCB layout, and module footprints added.
- FPGA UART, PWM, mouth animation, head return, tail movement, and stop command implemented in source.
- Voice, LCD feedback, and mouth movement reported working in the latest integration session.
- Head/tail motor interference remains under investigation: disconnecting J3 restored clean audio in the latest test. The precise electrical cause and final fix still need verification.
- Full completion video will be added after the remaining fixes and final demonstration.

**Source coverage:** the FPGA and hardware files are recovered from the local project. PC service source is included. The available Pi backup is dated **August 19, 2026** and is preserved as an explicitly dated snapshot; it does **not** contain all September changes or the latest LCD integration. See [source provenance and outstanding work](docs/STATUS.md).

## Explore the project

| Area | Files |
| --- | --- |
| Editable schematic and PCB | [KiCad project](hardware/kicad/Kevin_PCB.kicad_pro), [schematic](hardware/kicad/Kevin_PCB.kicad_sch), [PCB](hardware/kicad/Kevin_PCB.kicad_pcb) |
| Custom module footprints | [Kevin.pretty](hardware/kicad/Kevin.pretty) |
| Manufacturing exports | [Saved Gerber sets](hardware/fabrication) |
| Main FPGA controller | [Verilog](firmware/Kevin_motor_controller/src/kevin_motor_controller.v), [pin constraints](firmware/Kevin_motor_controller/src/kevin_motor_controller.cst), [Gowin project](firmware/Kevin_motor_controller/Kevin_motor_controller.gprj) |
| Earlier FPGA bring-up | [Mouth test](firmware/Kevin_motor_test), [UART](firmware/kevin_nano_uart), [LED blink](firmware/kevin_nano_blink) |
| PC voice and integration services | [PC software](software/pc) |
| Historical Pi code | [KevinOS — August 19 snapshot](software/archive/2026-08-19/KevinOS) |
| Original motor investigation | [Reverse-engineering notes](docs/REV001_ReverseEngineering.md) |

## Hardware and firmware

Open `hardware/kicad/Kevin_PCB.kicad_pro` in KiCad. Keep `Kevin.pretty` and `fp-lib-table` alongside the project so its custom footprints resolve. Saved fabrication exports are historical sets; their correspondence to the current board has not been verified. Regenerate fabrication files from a checked board before ordering.

Open the main controller `.gprj` in Gowin for the Tang Nano 9K. Source defaults assume a 27 MHz clock, approximately 115200-baud UART, and 1 kHz PWM. Motor timing and duty-cycle constants are specific to this mechanism.

| UART byte | Action |
| --- | --- |
| `q`, `n`, `N`, `e`, `E` | Quiet, normal short/long, and emphasis short/long mouth sequences |
| `H` | Head out |
| `h` | Head home |
| `T` | Tail sequence |
| `S` | Stop |

Acknowledgements identify recognized commands; they do not prove physical movement completed. The early reverse-engineering notes use motor labels from the original investigation; the main FPGA source calls the mouth channel A and head/tail channel B.

## Software

See [PC service setup](software/pc/README.md). The services cover Kokoro speech synthesis, faster-whisper transcription, and an optional Spotify/file-access bridge. Ollama supplies the language-model endpoint used by KevinOS.

The dated Pi snapshot is useful for understanding the earlier audio, AI, and motor architecture. It is not a complete reproduction of the present build. The current Pi source, dependency versions, and final demonstration remain to be synchronized.

## Validation

For this repository update, Python sources were checked for syntax and the main Verilog controller was compiled with Icarus Verilog. These checks do not establish hardware operation, timing closure, electrical correctness, or completion of the remaining integration fixes.
