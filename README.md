# Silent Hill DS+

Hi everyone! Silent Hill 1 is one of my favourite games, and I also really love this device, the RG DS. I took the Silent Hill source code and adapted it for two screens. I hope you enjoy it. You will find the installation instructions below.

If you enjoy it and would like to support me, here is my Boosty: https://boosty.to/aumvilohm

Silent Hill DS+ is an unofficial, non-commercial fan port of Silent Hill (PlayStation, 1999) to the Anbernic RG DS Plus running ROCKNIXDS. It is built on the community [Silent Hill PC Port](https://github.com/SlickAmogus/silent-hill-decomp/tree/pc-port), so it runs natively, not in an emulator. The game is on the top screen, and the original inventory runs live on the bottom screen, so the world keeps going while you pick items or look at the map.

It runs at a steady 30 FPS on both screens with the middle performance profile (CPU up to 1608 MHz, GPU up to 600 MHz).

This is an early release, so there may be bugs. Some of them come from the Silent Hill PC Port itself and happen there too.

## You need your own copy of the game

This repository has no Silent Hill game data: no disc image, BIOS, music, video, textures or text. I won't share game files or help anyone find them. Silent Hill is © Konami, so please respect their rights, and if you don't own the game, buy it.

Make a BIN/CUE image from your own PlayStation disc, where the law in your country allows it. I tested the port with the North American release, SLUS-00707 version 1.1, as one BIN and one CUE (BIN SHA-1 `34278d31d9b9b12b3b5db5e45bcbe548991ecbc7`, 616,494,480 bytes).

The prepare script in the release takes a BIN/CUE or the `.zip` it came in. A CHD has to be converted first, for example with `chdman extractcd -i "Silent Hill (USA).chd" -o "Silent Hill (USA).cue"`.

## Install

You need an RG DS Plus with ROCKNIXDS 1.6.3-plus (ROCKNIX 20261001) and about 650 MB free on it.

1. Download `SilentHill-DS-Plus-1.0.zip` from [Releases](https://github.com/aumVilohm/silent-hill-ds-plus/releases) and unzip it.
2. Put your disc image into the `game` folder: the `.bin` and `.cue`, or the `.zip` they came in.
3. Run the prepare script. On Windows, double-click `prepare.bat`. On macOS or Linux, open a terminal in the unzipped folder and run `sh prepare.sh`. It checks your image and puts it into the port folder.
4. Copy everything inside the `ports` folder into `roms/ports` on the console. If SSH is on, you can do it from the unzipped folder like this, where `<console>` is the console's address:
   ```sh
   COPYFILE_DISABLE=1 tar -cf - -C ports SilentHill.sh silent-hill-rgds-plus | ssh root@<console> 'tar -xf - -C /storage/roms/ports'
   ```
5. Restart the console and start SilentHill from Ports.

Saves go to `silent-hill-rgds-plus/gamedata/save/`. To quit, tap Exit on the bottom screen, then Yes. To update, copy the `ports` folder of the new release over the old one. You don't need to run prepare again: your saves and disc image stay, only the settings file is replaced.

## Controls

The controls follow the classic PlayStation layout: each button does what the button in the same place does on a PlayStation pad. The names below are the labels printed on the console.

| Button | PlayStation | In the game |
|---|---|---|
| B (bottom) | Cross | Action, attack, confirm |
| A (right) | Circle | Flashlight, cancel in menus |
| X (top) | Triangle | Map on the bottom screen |
| Y (left) | Square | Run |
| Start | Start | Pause |
| Select | Select | Switch the pad between Harry and the bottom screen |

D-pad or left stick moves Harry. L1, R1, L2 and R2 keep the original "Type A" layout.

The bottom screen always works by touch. You can pick items, use the original commands (Use, Equip, Unequip, Reload, On/Off, Look) and the bottom row: Map, Option and Exit. After Select the pad drives the bottom screen too: the D-pad moves, B confirms, and A, X or Y go back. Start still pauses the game. Option opens the original settings on the top screen, and Exit asks before quitting.

X opens the original paper map on the bottom screen instead of the inventory, and Harry keeps moving. Tap the arrows above and below the map to change floors, the square button with a cross to close it and the one with a magnifier to zoom. X closes the map too.

## Bugs and logs

If you find a bug, please open an issue here or write to me on Boosty, and send screenshots and the logs. The logs are in `roms/ports/silent-hill-rgds-plus/logs/`, one folder per run.

## Uninstall

Quit the game, delete `SilentHill.sh` and the `silent-hill-rgds-plus` folder from `roms/ports` and restart the console. This also deletes your saves and the disc image, so copy `silent-hill-rgds-plus/gamedata/save` first if you want to keep your saves.

## Build from source

This repository has the patches, the Ports launcher, the install scripts and the build tools. The upstream sources come from their own repositories at fixed commits. You need git, Python 3.9 or newer (the one that comes with macOS works) and Docker that can run `linux/arm64` containers (Docker Desktop on a Mac works). The build scripts expect the repository in a folder named `silent-hill`:

```sh
mkdir sh-rgds && cd sh-rgds
git clone https://github.com/aumVilohm/silent-hill-ds-plus.git silent-hill

# 1. Builder image: Ubuntu 24.04 arm64 with GCC 13, CMake, Ninja, SDL2, OpenAL, GLES/EGL, Wayland
docker build --platform linux/arm64 -t rgds-silent-hill-builder:ubuntu24.04 \
  -f silent-hill/tools/Dockerfile silent-hill/tools

# 2. Upstream sources at the pinned commits
git clone https://github.com/SlickAmogus/silent-hill-decomp.git silent-hill/upstream
git -C silent-hill/upstream checkout 60ed02045da3dbd3d5633e9528f33707b0f03c95
git -C silent-hill/upstream submodule update --init pc_port/PsyCross   # -> 20a2fb4798be6c57ebe799dc03e07338b5551563

# 3. Apply the patches
git -C silent-hill/upstream apply "$PWD/silent-hill/patches/silent-hill-rgds.patch"
git -C silent-hill/upstream/pc_port/PsyCross apply "$PWD/silent-hill/patches/psycross-rgds.patch"

# 4. Build (the container runs with --network none)
sh silent-hill/tools/build.sh

# 5. Package and make the release zip
python3 silent-hill/tools/package.py
python3 silent-hill/tools/make-release.py
```

The zip ends up in `silent-hill/dist/`, the same as the one on the Releases page. Then go on with [Install](#install) from step 2. You don't need the disc to build.

## Credits

- Konami, for Silent Hill (PlayStation, 1999). The game and all its content are © Konami.
- silent-hill-decomp and its contributors, for the decompilation: https://github.com/shdecompilations/silent-hill-decomp
- Chris Hardin and the Silent Hill PC Port contributors, for the PC port this is based on (branch `pc-port`, commit `60ed02045da3dbd3d5633e9528f33707b0f03c95`): https://github.com/SlickAmogus/silent-hill-decomp/tree/pc-port, https://sh1pc.com/
- PsyCross, the PS1 hardware layer (commit `20a2fb4798be6c57ebe799dc03e07338b5551563` of https://github.com/SlickAmogus/PsyCross), based on Psy-Cross by the REDRIVER2 Project (MIT): https://github.com/OpenDriver2/PsyCross
- Lua, miniz, stb_image and stb_truetype, cgltf and jsmn, xxHash, bcdec, glad, an MDEC decoder adapted from FFmpeg, the AVI reader and FMV player design from REDRIVER2 and the Shinonome bitmap font, all compiled in through upstream under their own licences. Their full licence texts are in `licenses/THIRD-PARTY-NOTICES` in the archive.
- SDL_GameControllerDB (zlib): https://github.com/gabomdq/SDL_GameControllerDB
- The Oswald and Barlow Semi Condensed fonts (SIL Open Font License 1.1).
- ROCKNIX (https://rocknix.org) and ROCKNIXDS, the firmware it runs on.

AI tools were among the tools I used in this project.

## Licences

My changes (`patches/silent-hill-rgds.patch`, `port/`, `tools/`) are under the GNU General Public License v3.0 or later, see [LICENSE](LICENSE). The PsyCross patch (`patches/psycross-rgds.patch`) is also offered under the MIT licence, see [LICENSES/MIT-psycross-rgds-patch.txt](LICENSES/MIT-psycross-rgds-patch.txt). The GPL covers only my additions: nobody licenses the decompiled Silent Hill code, and the few lines of it that show up as context in the patches remain Konami's. The Ports picture (`port/SilentHill.box.png`, drawn by `tools/make-ports-icon.py`) is my own work and uses nothing from the game apart from its name. This is a modified version of the Silent Hill PC Port, changed in 2026 for the Anbernic RG DS Plus. More details are in [COPYRIGHT.md](COPYRIGHT.md).

The release zip carries the same licences, plus the third-party notices, in `silent-hill-rgds-plus/licenses/`.

## Disclaimer

Silent Hill DS+ is an unofficial, non-commercial fan project. It is not affiliated with or endorsed by Konami, Sony Interactive Entertainment, Anbernic, the ROCKNIX project or the Silent Hill PC Port and silent-hill-decomp projects. SILENT HILL is a registered trademark of Konami Digital Entertainment Co., Ltd., and PlayStation is a registered trademark of Sony Interactive Entertainment Inc. The names are used only to describe what this is. Requests for game files will be closed. This software is provided "as is", without warranty of any kind.
