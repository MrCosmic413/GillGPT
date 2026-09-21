# Source provenance and remaining work

Repository update: September 20, 2026.

- `hardware/kicad`: Kevin_PCB project last saved September 2, including the two custom module footprints and project-relative footprint library table.
- `hardware/fabrication`: the two saved Kevin PCB Gerber/drill sets from the local GillGPT folder. Retained separately; neither is asserted to match the latest KiCad board.
- `firmware`: local Gowin projects and source files, including the main motor controller and earlier experiments. Generated build directories and user-specific IDE files are excluded.
- `software/pc`: recovered PC service scripts. The publishing copy replaces the embedded shared bridge key with `KEVIN_BRIDGE_KEY`, uses portable home-relative folders, and reads Spotify configuration from a local `.env`. A stray bracket and duplicate obsolete file-search/path-check functions in the recovered bridge were removed; the folder-alias-aware implementations are retained. The running PC files were not changed.
- `software/archive/2026-08-19/KevinOS`: Python source recovered from the August 19 Pi backup. Embedded bridge keys were replaced with `KEVIN_BRIDGE_KEY`. Personal conversation memory, OAuth cache, credentials, virtual environments, and generated files are excluded. This is a sanitized historical snapshot, not the September runtime.

## Latest reported integration state

On September 20, voice, LCD behavior, and mouth animation were reported working. Reintroducing the head/body path produced static; unplugging J3 restored clean speech. Motor noise, supply disturbance, and grounding remain candidate causes. A final electrical fix has not been verified in this repository update.

## Needed to finish synchronization

1. Retrieve the current `~/KevinOS` source from the Raspberry Pi, including the LCD code and latest audio/streaming changes.
2. Record the working dependency/model versions and launch configuration.
3. Verify the motor interference fix on hardware and update the status.
4. Add the new full demonstration video after recording it.

No hardware tests or fresh KiCad ERC/DRC were performed during this update. The local historical ERC report predates the final schematic save and is not presented as current validation.
