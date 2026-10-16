#!/usr/bin/env python3
"""Turn the Ports archive from package.py into the release zip.

  SilentHill-DS-Plus-<version>/
    HOW-TO-INSTALL.txt
    prepare.bat, prepare.ps1   Windows
    prepare.sh                 macOS and Linux
    game/                      the player puts the disc image here
    ports/                     copied into roms/ports on the console

The zip never contains a disc image. Entry times come from the Ports archive, so the
same archive always gives the same zip."""
import argparse
from pathlib import Path
import sys
import tarfile
import time
import zipfile

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--version', default='1.0')
parser.add_argument('--archive', help='Ports archive (default: the newest dist/SilentHill-RGDS-ports-*.tar.gz)')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
release = root / 'port/release'

if args.archive:
    archive = Path(args.archive)
else:
    found = sorted((root / 'dist').glob('SilentHill-RGDS-ports-*.tar.gz'), key=lambda p: p.stat().st_mtime)
    if not found:
        sys.exit('No dist/SilentHill-RGDS-ports-*.tar.gz. Run tools/package.py first.')
    archive = found[-1]

top = f'SilentHill-DS-Plus-{args.version}/'
out = root / 'dist' / f'SilentHill-DS-Plus-{args.version}.zip'
DISC = ('.bin', '.cue', '.iso', '.chd', '.pbp', '.img', '.mcd')


def entry(name, mtime, mode):
    info = zipfile.ZipInfo(name, date_time=mtime)
    info.create_system = 3
    info.external_attr = mode << 16
    if name.endswith('/'):
        info.external_attr |= 0x10
    else:
        info.compress_type = zipfile.ZIP_DEFLATED
    return info


def crlf(data):
    return data.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')


with tarfile.open(archive) as tar:
    members = [m for m in tar.getmembers() if m.isfile() or m.isdir()]
    if not any(m.name == 'silent-hill-rgds-plus/SilentHillPC' for m in members):
        sys.exit(f'{archive.name} has no silent-hill-rgds-plus/SilentHillPC')
    bad = [m.name for m in members if m.name.lower().endswith(DISC)]
    if bad:
        sys.exit(f'{archive.name} contains disc files: {bad}')

    mtime = time.gmtime(max(m.mtime for m in members))[:6]
    out.unlink(missing_ok=True)
    with zipfile.ZipFile(out, 'w', compresslevel=9) as z:
        z.writestr(entry(top, mtime, 0o40755), b'')
        for name, mode, windows in (('HOW-TO-INSTALL.txt', 0o100644, True), ('prepare.bat', 0o100644, True),
                                    ('prepare.ps1', 0o100644, True), ('prepare.sh', 0o100755, False)):
            data = (release / name).read_bytes()
            z.writestr(entry(top + name, mtime, mode), crlf(data) if windows else data)
        z.writestr(entry(top + 'game/', mtime, 0o40755), b'')
        z.writestr(entry(top + 'game/PUT-YOUR-GAME-HERE.txt', mtime, 0o100644),
                   crlf((release / 'PUT-YOUR-GAME-HERE.txt').read_bytes()))
        z.writestr(entry(top + 'ports/', mtime, 0o40755), b'')
        for m in sorted(members, key=lambda m: m.name):
            name = top + 'ports/' + m.name.lstrip('./')
            if m.isdir():
                z.writestr(entry(name.rstrip('/') + '/', mtime, 0o40000 | (m.mode & 0o777)), b'')
            else:
                z.writestr(entry(name, mtime, 0o100000 | (m.mode & 0o777)), tar.extractfile(m).read())

with zipfile.ZipFile(out) as z:
    names = z.namelist()
print(f'{out.relative_to(root)}: {len(names)} entries from {archive.name}')
