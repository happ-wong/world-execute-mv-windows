"""Drive the Windows audio engine (audio-clock.ps1) directly and print its clock.

    python tools/engine_client.py [--seek 100] [--seconds 5]
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / 'src' / 'audio-clock.ps1'
MP3 = ROOT / 'src' / 'media' / 'song.mp3'
SHELL = str(Path(sys.executable).parent)  # noqa - keep python discoverable
POWERSHELL = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=5.)
    parser.add_argument('--seek', type=float, default=100.)
    parser.add_argument('--volume', type=float, default=0.15)
    args = parser.parse_args()
    start = time.monotonic()
    proc = subprocess.Popen([POWERSHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
                             'Bypass', '-Sta', '-File', str(ENGINE), str(MP3)],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding='utf-8',
                            errors='replace', bufsize=1)

    def send(line):
        proc.stdin.write(line + '\n')
        proc.stdin.flush()

    import threading
    stderr_lines = []
    threading.Thread(target=lambda: stderr_lines.append(proc.stderr.read()),
                     daemon=True).start()

    first = proc.stdout.readline()
    print(f'handshake after {time.monotonic() - start:.2f}s -> {first.strip()}', flush=True)
    duration = json.loads(first)['duration']
    send(f'volume {args.volume}')
    send(f'seek {args.seek}')
    send('play')
    stamps = []
    deadline = time.monotonic() + args.seconds
    while time.monotonic() < deadline:
        line = proc.stdout.readline().strip()
        if not line:
            break
        state = json.loads(line)
        stamps.append((time.monotonic(), state['time'], state['playing']))
        if len(stamps) % 12 == 0:
            print(f"t={stamps[-1][1]:8.3f} playing={stamps[-1][2]}", flush=True)
    print(f'{len(stamps)} updates in {stamps[-1][0] - stamps[0][0]:.2f}s wall, '
          f'clock moved {stamps[-1][1] - stamps[0][1]:.3f}s '
          f'-> rate {(stamps[-1][1] - stamps[0][1]) / (stamps[-1][0] - stamps[0][0]):.4f}', flush=True)
    step_errors = [abs(b - a - (w2 - w1)) for (w1, a, _), (w2, b, _) in zip(stamps, stamps[1:])]
    print(f'largest per-message clock error: {max(step_errors) * 1000:.1f}ms', flush=True)
    send('pause')
    time.sleep(1.0)
    held = json.loads(proc.stdout.readline())['time']
    send('play')
    time.sleep(1.0)
    resumed = json.loads(proc.stdout.readline())['time']
    send('quit')
    proc.wait(timeout=10)
    print(f'pause held at {held:.3f}s (near {stamps[-1][1]:.3f}s), resume moved to {resumed:.3f}s',
          flush=True)
    print(f'exit code {proc.returncode}')
    print('stderr: ' + ('(none)' if not stderr_lines or not stderr_lines[0].strip()
                        else stderr_lines[0][:400]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
