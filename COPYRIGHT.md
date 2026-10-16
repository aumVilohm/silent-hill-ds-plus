# Copyright and licensing

Silent Hill DS+ is an unofficial, non-commercial fan project. It adapts the community
Silent Hill PC Port to the Anbernic RG DS Plus running ROCKNIXDS. This repository holds
only those changes (as patches), the Ports launcher, the build tools, the install
scripts and the documentation. It does not contain the PC port itself, the decompiled
game code or any game data.

## 1. My changes: GPL-3.0-or-later

Copyright (c) 2026 aumVilohm and contributors.

- `patches/silent-hill-rgds.patch`, `port/`, `tools/` and the documentation are licensed
  under the GNU General Public License, version 3 or (at your option) any later version.
  See [LICENSE](LICENSE). They have to be, since they modify the GPL-3.0-or-later Silent
  Hill PC Port.
- `patches/psycross-rgds.patch` (changes to PsyCross) is also offered under the MIT
  licence, like PsyCross itself, so it can go back upstream. See
  [LICENSES/MIT-psycross-rgds-patch.txt](LICENSES/MIT-psycross-rgds-patch.txt), and for
  PsyCross itself [LICENSES/MIT-PsyCross.txt](LICENSES/MIT-PsyCross.txt).
- `port/SilentHill.box.png` and `tools/make-ports-icon.py` are original work. Apart from
  the game's name in a plain pixel font, the picture contains nothing from the game.

Modification notice (GPL-3.0 section 5a): this is a modified version of the Silent Hill
PC Port, changed in October 2026 for the Anbernic RG DS Plus / ROCKNIXDS. Every change is
in `patches/`, against the pinned commits listed in `patches/manifest.json`.

## 2. What the GPL covers here, and what it does not

The patches to the decompiled sources (`src/`, `include/`) add code only inside
`#ifdef SH_PC_PORT` / `#ifdef SH_RGDS` blocks. The licence above covers that added code
and nothing else. It does not extend to the surrounding decompiled code, which nobody
licenses, me included. The few lines of it that appear as diff context in the patch files
remain Konami's.

A binary built from these sources contains compiled decompiled game code, so as a whole
it is not a GPL work. Its GPL-licensed parts (the PC-port code and my changes) are under
GPL-3.0-or-later, and their corresponding source is this repository plus the pinned
upstream commits.

## 3. Upstream projects

- Silent Hill PC Port by Chris Hardin and contributors, GPL-3.0-or-later:
  <https://github.com/SlickAmogus/silent-hill-decomp/tree/pc-port>. The patches apply to
  the commit pinned in `patches/manifest.json`.
- silent-hill-decomp, the community decompilation the PC port builds on. It claims no
  rights in the decompiled code; see its `COPYRIGHT.md`.
- PsyCross by the REDRIVER2 Project, MIT licence.
- The other components compiled into a build (for example Lua, miniz, stb, cgltf/jsmn,
  xxHash, ReadAVI, the MDEC decoder, the FMV player design from REDRIVER2 and the fonts)
  come with the upstream sources under their own licences; see upstream's `COPYRIGHT.md`.

## 4. The game

Silent Hill and all of its original code, characters, story, music, artwork and other
content are (c) Konami. SILENT HILL is a registered trademark of Konami Digital
Entertainment Co., Ltd. No game data, disc image or BIOS is included or provided. To play,
you need your own original copy of the game.
