#!/usr/bin/env python3
"""Build the Windows single-file player.

Usage:  python tools/build_bundle.py [--with-zip]

Produces dist/world-execute-mv-win.pyz (a zipapp whose resources are verified
against bundle-manifest.json at startup), plus an optional distributable zip and
SHA256SUMS.txt.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import zipfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
DIST = ROOT / 'dist'
TARGET = 'world-execute-mv-win.pyz'
# audio-clock is a Mach-O binary and winmm/MCI lives in the player itself.
SKIP = {'audio-clock', '__pycache__', '.DS_Store'}


def files():
    out = []
    for path in sorted(SRC.rglob('*')):
        if not path.is_file():
            continue
        name = path.relative_to(SRC).as_posix()
        if path.name in SKIP or '__pycache__' in path.parts:
            continue
        out.append(name)
    return out


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def manifest_payload(names):
    entries = {}
    for name in names:
        entries[name] = sha256((SRC / name).read_bytes())
    return {
        'format': 1,
        'platform': 'Windows 10+ / macOS 12+',
        'architectures': ['x64', 'arm64'],
        'audio_backend': {'windows': 'winmm MCI (mpegvideo)', 'macos': 'AVFoundation audio-clock'},
        'python': '3.9+',
        'files': entries,
    }


def build():
    names = files()
    for required in ('player.py', 'scenes.py', 'lyrics.json', 'spectrum.json',
                     'config.json', 'media/song.mp3', '__main__.py', 'audio-clock.ps1'):
        if required not in names:
            raise SystemExit(f'缺少资源：{required}')
    DIST.mkdir(exist_ok=True)
    staging = DIST / 'stage'
    if staging.exists():
        raise SystemExit(f'请先清空 {staging}')
    manifest = manifest_payload(names)
    staging.mkdir()
    try:
        for name in names:
            target = staging / Path(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((SRC / name).read_bytes())
        (staging / 'bundle-manifest.json').write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        archive = DIST / TARGET
        zipapp.create_archive(staging, target=archive, compressed=True)
    finally:
        import shutil
        shutil.rmtree(staging, ignore_errors=True)
    return archive, manifest


def verify(archive):
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        manifest = json.loads(bundle.read('bundle-manifest.json'))
        missing = [n for n in manifest['files'] if n not in names]
        extra = sorted(n for n in names if n not in manifest['files'] and not n.endswith('/'))
        broken = []
        for name, digest in manifest['files'].items():
            if name in names and sha256(bundle.read(name)) != digest:
                broken.append(name)
    return missing, extra, broken


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--with-zip', action='store_true', help='also build the distributable zip')
    args = parser.parse_args()
    if sys.version_info < (3, 9):
        raise SystemExit('需要 Python 3.9 或更新版本')
    archive, manifest = build()
    missing, extra, broken = verify(archive)
    print(f'built {archive.name}  {archive.stat().st_size:,} bytes')
    print('files:', ', '.join(sorted(manifest['files'])))
    if missing or broken:
        raise SystemExit(f'打包失败 missing={missing} broken={broken}')
    if extra:
        print('not covered by the manifest (informational):', ', '.join(extra))
    if args.with_zip:
        payload = [archive, ROOT / 'README.md', ROOT / 'player.cmd',
                   ROOT / '运行单文件.cmd', ROOT / '全屏播放.cmd']
        bundle_zip = DIST / 'world-execute-mv-windows.zip'
        sums = DIST / 'SHA256SUMS.txt'
        lines = []
        with zipfile.ZipFile(bundle_zip, 'w', zipfile.ZIP_DEFLATED) as out:
            for path in payload:
                if path.exists():
                    out.write(path, path.name)
                    lines.append(f'{sha256(path.read_bytes())} *{path.name}')
                else:
                    print(f'missing payload: {path}')
        sums.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'built {bundle_zip.name}  {bundle_zip.stat().st_size:,} bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
