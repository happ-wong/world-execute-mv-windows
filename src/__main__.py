"""Extract bundled media into a private temporary directory, then run the player.

Runs from a zipapp (``python world-execute-mv.pyz``) on Windows or macOS.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import runpy
import shutil
import sys
import tempfile
import time
import zipfile

MINIMUM = (3, 9)


def require_platform():
    if sys.version_info < MINIMUM:
        raise SystemExit('需要 Python 3.9 或更新版本，当前是 ' + platform.python_version() + '。')
    if sys.platform not in ('win32', 'darwin'):
        raise SystemExit('这个单文件播放器支持 Windows 和 macOS。')
    if sys.platform == 'win32' and sys.getwindowsversion().major < 10:
        raise SystemExit('需要 Windows 10 或更新版本（终端需要支持 VT 转义序列）。')


def extract(bundle, manifest, root):
    for name, digest in manifest['files'].items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise SystemExit('程序包资源路径无效。')
        data = bundle.read(name)
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit('程序包资源校验失败：' + name)
        target = root.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    if sys.platform != 'win32':
        clock = root / 'audio-clock'
        if clock.is_file():
            clock.chmod(0o755)


def cleanup(root):
    """Windows keeps the MP3 open briefly after MCI closes it, so retry before giving up."""
    deadline = time.monotonic() + 3
    while True:
        shutil.rmtree(root, ignore_errors=True)
        if not root.exists() or time.monotonic() > deadline:
            return
        time.sleep(.1)


def main():
    require_platform()
    archive = Path(sys.argv[0]).resolve()
    sys.dont_write_bytecode = True
    if not zipfile.is_zipfile(archive):
        raise SystemExit('请把此文件与播放器包放在一起运行，不要单独保存 __main__.py。')
    root = Path(tempfile.mkdtemp(prefix='world-execute-mv-'))
    try:
        with zipfile.ZipFile(archive) as bundle:
            manifest = json.loads(bundle.read('bundle-manifest.json'))
            if manifest.get('format') != 1:
                raise SystemExit('无法识别的程序包格式版本。')
            extract(bundle, manifest, root)
        sys.path.insert(0, str(root))
        sys.argv[0] = str(root / 'player.py')
        runpy.run_path(str(root / 'player.py'), run_name='__main__')
    finally:
        # Cleaned up here rather than by TemporaryDirectory: winmm keeps the MP3
        # handle alive briefly after the player closes, and that must not raise.
        cleanup(root)


if __name__ == '__main__':
    main()
