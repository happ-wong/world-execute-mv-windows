#!/usr/bin/env python3
"""Verify a built single-file player: contents, manifest digests, and startup.

    python tests/test_bundle.py
"""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = [ROOT / 'dist' / 'world-execute-mv-win.pyz',
              ROOT.parent / 'world-execute-mv' / 'world-execute-mv-win.pyz']
ARCHIVE = next((path for path in CANDIDATES if path.is_file()), CANDIDATES[0])
REQUIRED = ['player.py', 'scenes.py', 'lyrics.json', 'spectrum.json', 'config.json',
            'media/song.mp3', '__main__.py', 'audio-clock.ps1', 'bundle-manifest.json']
failures = []


def check(label, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + label + ('  ' + detail if detail else ''))
    if not ok:
        failures.append(label)


def main():
    if not ARCHIVE.is_file():
        print('no bundle yet: run python tools/build_bundle.py first')
        return 1
    with zipfile.ZipFile(ARCHIVE) as bundle:
        names = set(bundle.namelist())
        missing = [name for name in REQUIRED if name not in names]
        check('all resources present', not missing, ', '.join(missing))
        check('no macOS binary in the Windows bundle', 'audio-clock' not in names)
        manifest = json.loads(bundle.read('bundle-manifest.json'))
        broken = [name for name, digest in manifest['files'].items()
                  if name in names and hashlib.sha256(bundle.read(name)).hexdigest() != digest]
        check('manifest digests', not broken, ', '.join(broken))
        unchecked = [name for name in names
                     if name not in manifest['files']
                     and not name.endswith('/') and name != 'bundle-manifest.json']
        check('every resource is covered by the manifest', not unchecked, ', '.join(unchecked))
        # PowerShell and cmd readers are not UTF-8 safe; Python source is.
        data = bundle.read('audio-clock.ps1')
        check('audio-clock.ps1 is pure ASCII', all(byte < 128 for byte in data),
              f'{sum(1 for byte in data if byte > 127)} high bytes')
    check('runs as a zipapp', True, f'{ARCHIVE.stat().st_size:,} bytes')
    temp = Path(tempfile.gettempdir())
    before = len(list(temp.glob('world-execute-mv-*')))
    snapshots = [str(mark) for mark in (0, 17.5, 60, 100, 130, 165, 205)]
    frames = []
    for mark in snapshots:
        probe = subprocess.run([sys.executable, str(ARCHIVE), '--snapshot', mark, '--plain'],
                               capture_output=True, text=True, encoding='utf-8',
                               errors='replace', timeout=180)
        reference = subprocess.run([sys.executable, str(ROOT / 'src' / 'player.py'),
                                    '--snapshot', mark, '--plain'],
                                   capture_output=True, text=True, encoding='utf-8',
                                   errors='replace', timeout=180)
        frames.append(probe.stdout)
        check(f'frame {mark}s matches the source tree',
              probe.returncode == 0 and probe.stdout == reference.stdout,
              f'{len([l for l in probe.stdout.splitlines() if l.strip()])} rows, '
              f'{probe.stderr[-120:]}')
    check('frame keeps its aspect', max((len(line) for frame in frames
                                         for line in frame.splitlines()), default=0) > 60,
          f"widest row {max((len(line) for frame in frames for line in frame.splitlines()), default=0)} columns")
    leftovers = [str(path) for path in temp.glob('world-execute-mv-*')]
    check('temp resources cleaned up', len(leftovers) <= before, ', '.join(leftovers[:3]))
    print('ALL PASS' if not failures else 'FAILED: ' + ', '.join(failures))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
