#!/usr/bin/env python3
"""Save reproducible source patches without private disc data or build products.

The patches are written only after they have been applied to fresh clones of the pinned
upstream and PsyCross commits (cloned from the local repositories, no network) and the
result matches the working tree file for file."""
import argparse
import filecmp
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--build', default='build/arm64', help='Build directory whose SilentHillPC SHA-1 goes into the manifest, relative to silent-hill/ (default: build/arm64)')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
source = root / 'upstream'
psycross = source / 'pc_port/PsyCross'
directory = root / 'patches'
manifest = json.loads((directory / 'manifest.json').read_text())
NOTE = ('SHA-1 of SilentHillPC built by tools/build.sh. The build is reproducible '
        '(SOURCE_DATE_EPOCH = pinned upstream commit time).')

def git(cwd, *args, expected=(0,)):
    result = subprocess.run(['git', *args], cwd=cwd, capture_output=True)
    if result.returncode not in expected:
        raise RuntimeError(f'git {" ".join(args)} in {cwd.name}: ' + result.stderr.decode(errors='replace'))
    return result.stdout

def lines(output):
    return [line for line in output.decode().splitlines() if line]

def files_on_disk(tree):
    """Tracked and untracked, not ignored files as they are on disk (submodules excluded)."""
    names = set(lines(git(tree, 'ls-files', '--cached', '--others', '--exclude-standard')))
    names -= set(lines(git(tree, 'ls-files', '--deleted')))
    return {name for name in names if (tree / name).is_file() or (tree / name).is_symlink()}

def same(a, b):
    if a.is_symlink() or b.is_symlink():
        return a.is_symlink() and b.is_symlink() and os.readlink(a) == os.readlink(b)
    return (os.stat(a).st_mode & 0o111 != 0) == (os.stat(b).st_mode & 0o111 != 0) and filecmp.cmp(a, b, shallow=False)

trees = ((source, 'upstream', 'new_source_files'), (psycross, 'psycross', 'psycross_new_source_files'))
for tree, pin, key in trees:
    head = git(tree, 'rev-parse', 'HEAD').decode().strip()
    if head != manifest[pin]:
        sys.exit(f'{tree.relative_to(root)} is at {head}, not at the pinned {manifest[pin]}.')
    # A new file that is not listed would silently miss the patch, and a fresh clone would not build.
    missing = sorted(set(lines(git(tree, 'ls-files', '--others', '--exclude-standard'))) - set(manifest.get(key, [])))
    if missing:
        sys.exit(f'Untracked files in {tree.relative_to(root)} that patches/manifest.json "{key}" does not list:\n  '
                 + '\n  '.join(missing) + '\nList them there, or delete or ignore them.')
    git(tree, 'diff', 'HEAD', '--check')

patches = {}
patch = git(source, 'diff', 'HEAD', '--binary', '--', '.', ':(exclude)pc_port/PsyCross')
for path in manifest['new_source_files']:
    patch += git(source, 'diff', '--no-index', '--binary', '--', '/dev/null', path, expected=(1,))
patches['silent-hill-rgds.patch'] = patch
patch = git(psycross, 'diff', 'HEAD', '--binary')
for path in manifest.get('psycross_new_source_files', []):
    patch += git(psycross, 'diff', '--no-index', '--binary', '--', '/dev/null', path, expected=(1,))
patches['psycross-rgds.patch'] = patch

with tempfile.TemporaryDirectory(prefix='sh-rgds-clean-') as temp:
    clean = Path(temp) / 'upstream'
    git(root, 'clone', '--quiet', '--no-checkout', str(source), str(clean))
    git(clean, 'checkout', '--quiet', '--detach', manifest['upstream'])
    git(root, 'clone', '--quiet', '--no-checkout', str(psycross), str(clean / 'pc_port/PsyCross'))
    git(clean / 'pc_port/PsyCross', 'checkout', '--quiet', '--detach', manifest['psycross'])
    for name, data in patches.items():
        (Path(temp) / name).write_bytes(data)
    git(clean, 'apply', str(Path(temp) / 'silent-hill-rgds.patch'))
    git(clean / 'pc_port/PsyCross', 'apply', str(Path(temp) / 'psycross-rgds.patch'))
    for (tree, pin, _), fresh in zip(trees, (clean, clean / 'pc_port/PsyCross')):
        ours, theirs = files_on_disk(tree), files_on_disk(fresh)
        differ = sorted(ours ^ theirs) + sorted(name for name in ours & theirs if not same(tree / name, fresh / name))
        if differ:
            sys.exit(f'A fresh clone of {pin} with the patch differs from the working tree:\n  ' + '\n  '.join(differ[:40]))
        print(f'{pin}: fresh clone at {manifest[pin][:12]} + patch = working tree ({len(ours)} files compared)')

for name, data in patches.items():
    (directory / name).write_bytes(data)
manifest['local_binary_sha1'] = hashlib.sha1((root / args.build / 'SilentHillPC').read_bytes()).hexdigest()
manifest['note'] = NOTE
(directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
git(source, 'apply', '--reverse', '--check', str(directory / 'silent-hill-rgds.patch'))
git(psycross, 'apply', '--reverse', '--check', str(directory / 'psycross-rgds.patch'))
for name, data in patches.items():
    print(f'{name}: SHA-1 {hashlib.sha1(data).hexdigest()}')
print('Source patches verified; executable SHA-1 in', args.build + ':', manifest['local_binary_sha1'])
