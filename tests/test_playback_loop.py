#!/usr/bin/env python3
"""End-to-end test of the real play loop with a real audio clock.

Keyboard input is scripted and the terminal is stubbed, so this runs headless
while still exercising frame rendering, the audio subprocess, seeking, pausing
and the quit path.

    python tests/test_playback_loop.py
"""
from __future__ import annotations
import argparse
import io
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
import player  # noqa: E402


class ScriptedKeys:
    """Stands in for player.Keys: releases each scripted key at its scheduled time."""
    def __init__(self, script):
        self.start = time.monotonic()
        self.script = list(script)
        self.ready = None
        self.released = []

    def pending(self, delay):
        end = time.monotonic() + delay
        while True:
            if self.ready is not None:
                return True
            now = time.monotonic() - self.start
            if self.script and now >= self.script[0][0]:
                at, text = self.script.pop(0)
                self.ready = text
                self.released.append((round(now, 2), repr(text)))
                return True
            if time.monotonic() >= end:
                return False
            time.sleep(.004)

    def read(self):
        text, self.ready = self.ready or '', None
        return text


class Terminal(io.StringIO):
    encoding = 'utf-8'

    def fileno(self):
        raise OSError('no terminal in this test')

    def flush(self):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--volume', type=float, default=0.08)
    args = parser.parse_args()
    failures = []

    def check(label, ok, detail=''):
        print(('PASS ' if ok else 'FAIL ') + label + ('  ' + detail if detail else ''))
        if not ok:
            failures.append(label)

    film = player.Film()
    duration = film.config['duration']
    terminal = Terminal()
    keys = ScriptedKeys([(1.0, ' '), (3.5, ' '), (5.0, ' '), (6.0, '\x1b[D'), (7.5, 'q')])
    player.open_terminal = lambda: (lambda: None)
    player.Keys = lambda stream: keys
    real_stdout, sys.stdout = sys.stdout, terminal
    report = Path(tempfile.gettempdir()) / 'wemv-loop-report.json'
    options = argparse.Namespace(audio=str(ROOT / 'src' / 'media' / 'song.mp3'), start=0.,
                                autoplay=False, fps=24, paused=False, offset=None,
                                snapshot=None, width=100, height=36, plain=False,
                                report=str(report), stop_after=12., audio_latency=0.)
    crashed = None
    try:
        player.run(options, film)
    except BaseException as error:            # noqa: BLE001 - reported below
        crashed = error
    finally:
        sys.stdout = real_stdout
    frame = terminal.getvalue()
    check('loop exits cleanly on Q', crashed is None, repr(crashed))
    samples = json.loads(report.read_text(encoding='utf-8')) if report.is_file() else {}
    rows = samples.get('samples', [])
    check('report written', bool(rows), f'{len(rows)} samples, {samples.get("frames", 0)} frames')
    check('keys were released', len(keys.released) == 5, str(keys.released))
    check('alternate screen entered', '\x1b[?1049h' in frame)
    check('cursor parked home each frame', frame.count('\x1b[H') > 20, f"{frame.count(chr(27)+'[H')} frames")
    check('256 colour palette used', '\x1b[1;38;5;221m' in frame and '\x1b[0;38;5;215m' in frame)
    check('autowrap disabled, restored', '\x1b[?7l' in frame and '\x1b[?7h' in frame)
    check('cursor hidden, restored', '\x1b[?25l' in frame and '\x1b[?25h' in frame)
    check('title bar text drawn', 'WORLD.EXECUTE(ME);' in frame)
    check('captions rendered', 'PROTECTION' in frame or 'Switch on the power line' in frame)
    check('spectrum row rendered', any(mark in frame for mark in ('_|', ':|', '=|')))
    check('no stray CR/LF scroll', frame.count('\r\n') < 5, f"{frame.count(chr(13)+chr(10))}")
    times = [row['audio_time'] for row in rows]
    playing = [row['playing'] for row in rows]
    check('audio clock advanced', max(times) - min(times) > 2.0,
          f'{min(times):.2f}s .. {max(times):.2f}s' if times else 'no samples')
    # Samples are 30 frames apart, so a pair with no pause in between moves ~1.25s.
    rates = [(b - a) / (30 / options.fps) for a, b in zip(times, times[1:]) if 0 < b - a < 3]
    check('clock tracks wall time at 1x', bool(rates) and any(.8 < r < 1.2 for r in rates),
          ' '.join(f'{r:.2f}' for r in rates) + ' (pause pairs are expected to be lower)')
    check('space started playback', any(playing), str(playing))
    check('playback paused then resumed', False in playing and playing.count(True) > 1, str(playing))
    drops = [(a, b) for a, b in zip(times, times[1:]) if b < a - 1]
    check('arrow key seeked backwards', bool(drops), str(drops[:2]))
    check('rendering fast enough for 24fps', samples.get('max_frame_render_seconds', 1) < .05,
          f"slowest frame {samples.get('max_frame_render_seconds', 0) * 1000:.1f}ms")
    check('clock stayed inside the song', all(0 <= t <= duration for t in times),
          f'duration {duration:.2f}s')
    print('ALL PASS' if not failures else 'FAILED: ' + ', '.join(failures))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
