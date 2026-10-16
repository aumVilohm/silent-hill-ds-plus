#!/usr/bin/env python3
"""Stage the RG DS Plus Ports package and write the distributable archive.

Layout (mirrors /storage/roms/ports on the console):
  dist/ports/SilentHill.sh                 Ports entry
  dist/ports/silent-hill-rgds-plus/        everything the port owns
The archive is built from an explicit file list: the program, its settings, the two menu
fonts, the Ports picture and the licence texts. It never contains a disc image, saves,
logs or files derived from Konami data. Your own disc is linked into the local staging
folder only, with --with-disc."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--with-disc', action='store_true', help='Link your own BIN/CUE from silent-hill/gamedata/ into the staging folder (never into the archive)')
parser.add_argument('--test-scene', metavar='MAP', help='Boot straight into this map with the upstream test items (for testing, e.g. map3_s01)')
parser.add_argument('--render', choices=('native', '1024x768'), default='1024x768', help='Top-screen internal 3D resolution')
parser.add_argument('--fps', choices=('30', '60'), default='30', help='Top-screen frame cap in gameplay (30 = the original rate)')
parser.add_argument('--build', default='build/arm64', help='Build directory, relative to silent-hill/ (default: build/arm64)')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
build = root / args.build
upstream = root / 'upstream'
pc_port = upstream / 'pc_port'
ports = root / 'dist/ports'
package = ports / 'silent-hill-rgds-plus'
PREFIX = 'silent-hill-rgds-plus/'
disc = []
if args.with_disc:
    disc = sorted(p for p in (root / 'gamedata').glob('*') if p.is_file() and p.suffix.lower() in ('.bin', '.cue'))
    if not any(p.suffix.lower() == '.bin' for p in disc):
        sys.exit('--with-disc: no .bin disc image in silent-hill/gamedata/. Put your own BIN/CUE there first.')
pins = json.loads((root / 'patches/manifest.json').read_text())

# pc_port/assets/gamedata holds more than the port needs here. Only the two TrueType menu
# fonts (SIL OFL) are shipped. The rest is derived from Konami data, comes without a
# licence, or is unused on this device with the USA disc:
#   title/us.tim, title/pal.tim   title art for a title style that is not the disc's own
#   font/eur16.tim                PAL font atlas, for languages the disc does not carry
#   lang/*.lang, lang/zh.pack     translations of the game script
#   sound/*.wav, ra/sym.*.txt     RetroAchievements (off in this build)
#   decal.png                     bullet-hole decals (bullet_decals = 0)
GAMEDATA = ('font/BarlowSemiCondensed-Regular.ttf', 'font/Oswald-Regular.ttf')
NEVER_GAMEDATA = ('title', 'lang', 'ra', 'sound', 'font/eur16.tim', 'decal.png')
NEVER = re.compile(r'gamedata/(title|lang|ra|sound)(/|$)|eur16\.tim$|decal\.png$|\.lang$|zh\.pack$|\.wav$|/sym\.[^/]*\.txt$')
DISC_SUFFIXES = ('.bin', '.cue', '.iso', '.chd', '.pbp', '.img', '.mcd')
LICENCES = ('COPYRIGHT', 'LICENSE', 'LICENSE-SDL_GameControllerDB.txt', 'OFL.txt', 'THIRD-PARTY-NOTICES')
EXECUTABLE = re.compile(r'(^SilentHill\.sh|/SilentHillPC|\.so)$')


def git(*command):
    return subprocess.run(['git', '-C', str(upstream), *command], capture_output=True, text=True).stdout.strip()


def excerpt(path, first, last):
    """A licence block from a source file, from the line containing `first` to the next
    line containing `last`, without the comment decoration."""
    lines = path.read_text(encoding='utf-8').splitlines()
    start = next(i for i, line in enumerate(lines) if first in line)
    end = next(i for i in range(start, len(lines)) if last in lines[i])
    return '\n'.join(re.sub(r'^(/\*|\s?\*(?!/))\s?', '', line).rstrip() for line in lines[start:end + 1]).strip('\n')


MIT = '''Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.'''


def third_party_notices():
    src, inc = pc_port / 'src', pc_port / 'include'
    lua = pc_port / 'third_party/lua/src/lua.h'
    lua_version = '.'.join(re.search(rf'#define LUA_VERSION_{part}\s+"(\d+)"', lua.read_text()).group(1)
                           for part in ('MAJOR', 'MINOR', 'RELEASE'))
    stb_end = 'WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.'
    stb = excerpt(inc / 'stb_image.h', 'This software is available under 2 licenses', stb_end)
    if stb != excerpt(inc / 'stb_truetype.h', 'This software is available under 2 licenses', stb_end):
        sys.exit('stb_image.h and stb_truetype.h no longer carry the same licence; update package.py')
    if 'Shinonome 16-dot' not in (src / 'kanji_font.inc').read_text(encoding='utf-8')[:400]:
        sys.exit('pc_port/src/kanji_font.inc no longer names the Shinonome font; update package.py')
    sections = [
        ('PsyCross (PS1 hardware abstraction layer), pc_port/PsyCross, MIT',
         (pc_port / 'PsyCross/LICENSE').read_text(encoding='utf-8').strip()),
        ('My changes to PsyCross (patches/psycross-rgds.patch), also offered under MIT',
         (root / 'LICENSES/MIT-psycross-rgds-patch.txt').read_text(encoding='utf-8').strip()),
        (f'Lua {lua_version}, pc_port/third_party/lua (statically linked), MIT',
         excerpt(lua, '* Copyright (C) 1994-', 'SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.')),
        ('miniz, pc_port/src/miniz.c and include/miniz.h, MIT',
         excerpt(src / 'miniz.c', 'Copyright 2013-2014 RAD Game Tools', ' THE SOFTWARE.')),
        ('cgltf, pc_port/include/cgltf.h, MIT',
         excerpt(inc / 'cgltf.h', 'cgltf is distributed under MIT license', ' SOFTWARE.')),
        ('jsmn (embedded in cgltf.h; https://github.com/zserge/jsmn), MIT',
         'Copyright (c) 2010 Serge A. Zaitsev\n\n' + MIT),
        ('stb_image and stb_truetype, pc_port/include/stb_image.h and stb_truetype.h, MIT or public domain', stb),
        ('xxHash, pc_port/include/xxhash.h, BSD-2-Clause',
         excerpt(inc / 'xxhash.h', 'Copyright (C) 2012-2023 Yann Collet', 'OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.')),
        ('bcdec, pc_port/include/bcdec.h, MIT or public domain',
         excerpt(inc / 'bcdec.h', 'This software is available under 2 licenses', 'please refer to <https://unlicense.org>')),
        ('ReadAVI, pc_port/src/fmv/ReadAVI.cpp (AVI reader of the FMV player), BSD-3-Clause',
         excerpt(src / 'fmv/ReadAVI.cpp', 'Copyright (c) 2004-2013, Michael Kohn', 'POSSIBILITY OF SUCH DAMAGE.')),
        ('FMV player, pc_port/src/fmv/fmv_player.cpp, adapted from the REDRIVER2 VideoPlayer',
         'The PC port describes its FMV player as "adapted from REDRIVER2\'s VideoPlayer (BSD\n'
         'licensed)". The REDRIVER2 repository (https://github.com/OpenDriver2/REDRIVER2) is\n'
         'licensed as follows; the BSD-3-Clause AVI reader that came with the player is above.\n\n'
         'MIT License\n\nCopyright (c) 2020 SoapyMan\n\n' + MIT),
        ('MDEC decoder, pc_port/src/fmv/mdec.c, adapted from FFmpeg, LGPL-2.1-or-later',
         'Adapted from FFmpeg libavcodec/mdec.c ("Sony PlayStation MDEC (Motion DECoder)",\n'
         'Copyright (c) 2003 Michael Niedermayer, based upon code from Sebastian\n'
         'Jedruszkiewicz) with the MPEG-1 RL VLC tables from libavcodec/mpeg12data.c\n'
         '(copyright (c) 2000,2001 Fabrice Bellard, copyright (c) 2002-2004 Michael\n'
         'Niedermayer). FFmpeg is licensed under the GNU Lesser General Public License,\n'
         'version 2.1 or later; as LGPL-2.1 section 3 allows, the PC port uses this code under\n'
         'GPL-3.0-or-later (see LICENSE). Source: https://ffmpeg.org/'),
        ('glad 0.1.36, generated OpenGL / OpenGL ES loader, pc_port/PsyCross/src/render/glad.c',
         'Generated by glad 0.1.36 (https://github.com/Dav1dde/glad). glad states that its\n'
         'generated code is any of Public Domain, WTFPL or CC0, and that it is generated from\n'
         'the Khronos API registry:\n\n'
         '    Copyright (c) 2013-2020 The Khronos Group Inc.\n\n'
         '    Licensed under the Apache License, Version 2.0 (the "License");\n'
         '    you may not use this file except in compliance with the License.\n'
         '    You may obtain a copy of the License at\n\n'
         '        http://www.apache.org/licenses/LICENSE-2.0\n\n'
         '    Unless required by applicable law or agreed to in writing, software\n'
         '    distributed under the License is distributed on an "AS IS" BASIS,\n'
         '    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n'
         '    See the License for the specific language governing permissions and\n'
         '    limitations under the License.'),
        ('Bitmap fonts compiled into SilentHillPC',
         '- Japanese text (pc_port/src/kanji_font.inc): the Shinonome 16-dot JIS X 0208 bitmap\n'
         '  font, public domain (Yasuyuki Furukawa / the efont project,\n'
         '  http://openlab.ring.gr.jp/efont/).\n'
         '- Chinese glyphs (pc_port/src/kanji_font_cn.inc): from the Chinese fan translation\n'
         '  of Silent Hill (goro / 十三月, 2006). The PC port states that its Chinese material\n'
         '  is redistributed with the translators\' permission.\n'
         '- Debug overlay: IBM PC 8x8 bitmap font, public domain (pc_port/src/dbg_overlay.c).'),
        ('Other code credited in the sources',
         '- PsyCross SPU reverb (src/audio/PsyX_SPUReverb.*): its comments say it is ported from\n'
         '  DuckStation\'s SPU (https://github.com/stenzek/duckstation, src/core/spu.cpp), which\n'
         '  itself credits Mednafen-PSX.\n'
         '- PsyCross half-float conversion (src/gte/half_float.cpp): after\n'
         '  https://gist.github.com/rygorous/2156668 (Fabian Giesen).'),
        ('Not included: libraries from the firmware',
         'SilentHillPC is dynamically linked against SDL2 (zlib), OpenAL Soft (LGPL-2.0-or-later),\n'
         'libjpeg (IJG / libjpeg-turbo), libwayland-client (MIT), libstdc++, libgcc and glibc.\n'
         'They are part of ROCKNIX / ROCKNIXDS and are not in this archive.'),
        ('Also in this folder',
         '- OFL.txt: the Oswald and Barlow Semi Condensed fonts in gamedata/font/ (SIL OFL 1.1).\n'
         '- LICENSE-SDL_GameControllerDB.txt: gamecontrollerdb.txt (zlib).'),
    ]
    text = ('Third-party notices for the Silent Hill DS+ Ports archive\n'
            'Licence texts of components compiled into SilentHillPC and maps/*.so, reproduced\n'
            'from the Silent Hill PC Port sources at the pinned commit unless stated otherwise.\n')
    for title, body in sections:
        if not body.strip():
            sys.exit(f'empty licence text for {title}; update package.py')
        text += '\n' + '=' * 88 + '\n' + title + '\n' + '=' * 88 + '\n\n' + body + '\n'
    return text


def copyright_text(binary_sha1, epoch):
    patch_sha1 = {name: hashlib.sha1((root / 'patches' / name).read_bytes()).hexdigest()
                  for name in ('silent-hill-rgds.patch', 'psycross-rgds.patch')}
    return f'''Silent Hill DS+ for the Anbernic RG DS Plus (ROCKNIXDS): the Ports archive
==========================================================================

Silent Hill DS+ is an unofficial, non-commercial fan project. Silent Hill and all of its
original code, characters, story, music, artwork and other content are (c) Konami.
This archive contains no game data, disc image or BIOS. You need your own copy of the game.

What is in this archive, and under which terms
- SilentHill.sh, README-RGDS.txt, SilentHill.box.png and config.cfg (the PC port's
  configuration with RG DS Plus settings): GPL-3.0-or-later, see LICENSE.
- SilentHillPC and maps/*.so: the Silent Hill PC Port with my RG DS Plus changes, compiled
  for ARM64. They contain compiled decompiled Silent Hill code, which nobody licenses, me
  included, so these programs are not, as a whole, a GPL work. Their GPL-licensed parts
  (the PC-port code and my changes) are under GPL-3.0-or-later. The third-party code
  compiled into them keeps its own licence; see THIRD-PARTY-NOTICES.
- gamedata/font/: Oswald and Barlow Semi Condensed, SIL Open Font License 1.1 (OFL.txt).
- gamecontrollerdb.txt: SDL_GameControllerDB, zlib licence
  (LICENSE-SDL_GameControllerDB.txt).

Modification notice (GPL-3.0 section 5a): this is a modified version of the Silent Hill PC
Port, changed in 2026 for the Anbernic RG DS Plus / ROCKNIXDS.

Corresponding source (GPL-3.0 section 6)
- My patches, launcher and build scripts: https://github.com/aumVilohm/silent-hill-ds-plus
  patches/silent-hill-rgds.patch  SHA-1 {patch_sha1['silent-hill-rgds.patch']}
  patches/psycross-rgds.patch     SHA-1 {patch_sha1['psycross-rgds.patch']}
- applied to the Silent Hill PC Port, https://github.com/SlickAmogus/silent-hill-decomp
  (branch pc-port), commit {pins['upstream']},
  and its PsyCross submodule, commit {pins['psycross']}.
- Built with tools/build.sh (Docker, Ubuntu 24.04 arm64), SOURCE_DATE_EPOCH={epoch}.
  SilentHillPC SHA-1: {binary_sha1}

The source repository's COPYRIGHT.md follows. Paths in it refer to that repository.

------------------------------------------------------------------------------------------

''' + (root / 'COPYRIGHT.md').read_text(encoding='utf-8')


def ofl_text():
    text = (build / 'licenses/OFL.txt').read_text(encoding='utf-8')
    barlow = 'Copyright 2017 The Barlow Project Authors (https://github.com/jpt/barlow)'
    if barlow not in text:
        first, rest = text.split('\n', 1)
        text = first + '\n' + barlow + '\n' + rest
    return text


# Staging: everything the archive will contain, plus (locally only) your disc.
files = {}  # archive name -> file in the staging folder
def stage(name, source):
    target = ports / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    files[name] = target

package.mkdir(parents=True, exist_ok=True)
for name in NEVER_GAMEDATA:  # left over in the staging folder by older versions of this script
    stale = package / 'gamedata' / name
    if stale.is_dir():
        shutil.rmtree(stale)
    elif stale.exists():
        stale.unlink()
shutil.rmtree(package / 'licenses', ignore_errors=True)
stage('SilentHill.sh', root / 'port/SilentHill.sh')
stage(PREFIX + 'README-RGDS.txt', root / 'port/README-RGDS.txt')
stage(PREFIX + 'SilentHill.box.png', root / 'port/SilentHill.box.png')  # original pixel art (tools/make-ports-icon.py)
stage(PREFIX + 'SilentHillPC', build / 'SilentHillPC')
for module in sorted((build / 'maps').glob('*.so')):
    stage(PREFIX + 'maps/' + module.name, module)
for name in GAMEDATA:
    stage(PREFIX + 'gamedata/' + name, build / 'gamedata' / name)
stage(PREFIX + 'gamecontrollerdb.txt', build / 'gamecontrollerdb.txt')

config = (pc_port / 'config.cfg').read_text()
overrides = {
    # A Ports launch opens the original main menu (New Game / Load); logos are skipped.
    'map': args.test_scene or 'map0_s00', 'skip_intros': '2' if args.test_scene else '1', 'fps_cap': args.fps,
    'native_resolution': '1' if args.render == 'native' else '0',
    'renderer': 'gles', 'preload_chunks': '0', 'enable_plugins': '0',
    'show_console': '0', 'enable_debug_log': '1',
    'discord_rich_presence': '0', 'allow_debug_controls': '0',
    'rgds_swap_face_buttons': '2', 'rgds_map_bottom': '1', 'config_version': '3',
    # Original PS1 behaviour, the RG DS Plus defaults:
    # vanilla 8+2 VRAM chunk-texture pool instead of one GL texture per palette row
    # (far fewer draws a frame and less memory), retail culling, per-map character
    # loading, no PC-only extras.
    'resident_textures': '0', 'disable_culling': '0', 'global_chara_pool': '0',
    'dark_harry': '0', 'pc_port_credits': '0', 'weather_sim_hz': '30',
}
for key, value in overrides.items():
    pattern = rf'(?m)^{re.escape(key)}\s*=.*$'
    line = f'{key} = {value}'
    config = re.sub(pattern, line, config) if re.search(pattern, config) else config + '\n' + line + '\n'
(package / 'config.cfg').write_text(config)
files[PREFIX + 'config.cfg'] = package / 'config.cfg'

binary_sha1 = hashlib.sha1((package / 'SilentHillPC').read_bytes()).hexdigest()
epoch = int(os.environ.get('SOURCE_DATE_EPOCH') or git('log', '-1', '--format=%ct') or 0)
licences = {
    'LICENSE': (root / 'LICENSE').read_text(encoding='utf-8'),
    'COPYRIGHT': copyright_text(binary_sha1, epoch),
    'THIRD-PARTY-NOTICES': third_party_notices(),
    'OFL.txt': ofl_text(),
    'LICENSE-SDL_GameControllerDB.txt': (build / 'licenses/LICENSE-SDL_GameControllerDB.txt').read_text(encoding='utf-8'),
}
(package / 'licenses').mkdir()
for name, text in licences.items():
    (package / 'licenses' / name).write_text(text, encoding='utf-8')
    files[PREFIX + 'licenses/' + name] = package / 'licenses' / name

if args.with_disc:
    for source in disc:
        target = package / 'gamedata' / source.name
        if target.exists() and not os.path.samefile(source, target):
            target.unlink()
        if not target.exists():
            try:
                os.link(source, target)
            except OSError:
                shutil.copy2(source, target)
        print('Local user data (private, not in the archive):', target.relative_to(root))

# The archive: sorted entries, owner 0:0 without names, one fixed time, no gzip name or time.
def entry(name, kind, mode, size=0):
    info = tarfile.TarInfo(name)
    info.type, info.mode, info.size, info.mtime = kind, mode, size, epoch
    info.uid = info.gid = 0
    info.uname = info.gname = ''
    return info

directories = {str(parent) for name in files for parent in Path(name).parents if str(parent) != '.'}
archive = root / 'dist' / f'SilentHill-RGDS-ports-{binary_sha1[:12]}.tar.gz'
for old in (root / 'dist').glob('SilentHill-RGDS-ports-*.tar.gz'):
    if old != archive:
        old.unlink()
with archive.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as packed, \
        tarfile.open(fileobj=packed, mode='w', format=tarfile.USTAR_FORMAT) as tar:
    for name in sorted(directories | set(files)):
        if name in directories:
            tar.addfile(entry(name, tarfile.DIRTYPE, 0o755))
        else:
            with files[name].open('rb') as data:
                tar.addfile(entry(name, tarfile.REGTYPE, 0o755 if EXECUTABLE.search(name) else 0o644,
                                  files[name].stat().st_size), data)

# Audit what was actually written.
with tarfile.open(archive) as tar:
    members = tar.getmembers()
names = [m.name for m in members]
problems = []
if sorted(set(names) - directories) != sorted(files) or len(names) != len(set(names)):
    problems.append('archive entries differ from the file list')
for m in members:
    lower = m.name.lower()
    if (m.uid, m.gid, m.uname, m.gname) != (0, 0, '', ''):
        problems.append(f'owner not 0:0 without names: {m.name}')
    if lower.endswith(DISC_SUFFIXES + ('.log', '.tmp')) or {'save', 'logs'} & set(lower.split('/')):
        problems.append(f'disc image, save or log: {m.name}')
    if NEVER.search(m.name):
        problems.append(f'Konami-derived or unlicensed data: {m.name}')
gamedata = sorted(n[len(PREFIX + 'gamedata/'):] for n in names if n.startswith(PREFIX + 'gamedata/') and n not in directories)
if gamedata != sorted(GAMEDATA):
    problems.append(f'gamedata/ is not exactly the two fonts: {gamedata}')
shipped = sorted(n[len(PREFIX + 'licenses/'):] for n in names if n.startswith(PREFIX + 'licenses/') and n not in directories)
if shipped != sorted(LICENCES):
    problems.append(f'licenses/ is not {sorted(LICENCES)}: {shipped}')
for needle, where in (('GNU GENERAL PUBLIC LICENSE', 'LICENSE'), ('Version 3, 29 June 2007', 'LICENSE'),
                      ('The Oswald Project Authors', 'OFL.txt'), ('The Barlow Project Authors', 'OFL.txt'),
                      ('Sam Lantinga', 'LICENSE-SDL_GameControllerDB.txt'), (binary_sha1, 'COPYRIGHT'),
                      *((component, 'THIRD-PARTY-NOTICES') for component in
                        ('REDRIVER2 Project', 'Lua.org, PUC-Rio', 'Rich Geldreich', 'Johannes Kuhlmann',
                         'Serge A. Zaitsev', 'Sean Barrett', 'Yann Collet', 'Sergii Kudlai', 'Michael Kohn',
                         'SoapyMan', 'FFmpeg', 'glad 0.1.36', 'Shinonome'))):
    if needle not in licences[where]:
        problems.append(f'{where} lacks "{needle}"')
if problems:
    archive.unlink()
    sys.exit('Archive check failed, archive removed:\n  ' + '\n  '.join(problems))

manifest = {
    'binary_sha1': binary_sha1,
    'build': args.build,
    'map_modules': len(list((package / 'maps').glob('*.so'))),
    'archive': archive.name,
    'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    'archive_entries': len(names),
    'archive_files': len(files),
    'source_date_epoch': epoch,
    'top_render': args.render, 'fps_cap': args.fps, 'start': args.test_scene or 'main menu',
    'disc_in_staging': bool(disc) and all((package / 'gamedata' / p.name).exists() for p in disc),
    'disc_in_archive': False,
}
(root / 'dist' / 'ports-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('Staged:', ports.relative_to(root))
print('Archive checked: owners 0:0, no disc images, saves, logs or Konami-derived data files; all licence files present.')
print(json.dumps(manifest, indent=2))
