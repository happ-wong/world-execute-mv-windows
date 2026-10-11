#!/usr/bin/env python3
"""Headless checks for the audio clock on this machine. Plays audio quietly.

    python tests/test_audio_clock.py [--seconds 4] [--volume 0.1]

Covers the protocol the player depends on: duration handshake, a clock that runs
at 1x without jitter, seek landing, pause holding, resume continuing, volume, the
end-of-track report, and that the child process releases the MP3 on quit.
"""
from __future__ import annotations
import argparse
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=4.)
    parser.add_argument('--volume', type=float, default=0.1)
    args = parser.parse_args()
    import player

    class Options:
        audio_latency = 0.0

    failures = []

    def check(label, ok, detail=''):
        print(('PASS ' if ok else 'FAIL ') + label + ('  ' + detail if detail else ''))
        if not ok:
            failures.append(label)

    work = Path(tempfile.mkdtemp(prefix='wemv-test-'))
    copy = work / 'song.mp3'
    shutil.copyfile(ROOT / 'src' / 'media' / 'song.mp3', copy)
    started = time.monotonic()
    audio = player.make_audio(Options(), copy)
    check('engine starts', True, f'{time.monotonic() - started:.2f}s handshake, '
                                 f'{"windows" if player.IS_WINDOWS else "macos"} backend')
    audio.command(f'volume {args.volume}')
    duration = audio.state['duration']
    check('duration matches the song', abs(duration - 211.907) < .5, f'{duration:.3f}s')

    audio.command('seek 40')
    audio.command('play')
    samples = []
    deadline = time.monotonic() + args.seconds
    while time.monotonic() < deadline:
        time.sleep(.05)
        samples.append((time.monotonic(), audio.state['time']))
    t0, c0 = samples[0]
    wall = samples[-1][0] - t0
    moved = samples[-1][1] - c0
    rate = moved / wall if wall else 0
    check('clock runs at 1x', 0.93 < rate < 1.07, f'rate={rate:.4f} ({moved:.2f}s in {wall:.2f}s)')
    expected = c0 + (samples[-1][0] - t0)
    error = abs(samples[-1][1] - expected)
    check('clock is smooth', error < .15, f'drift {error * 1000:.1f}ms over {wall:.1f}s')
    check('clock is monotonic', all(b >= a - 1e-9 for (_, a), (_, b) in zip(samples, samples[1:])))
    check('clock messages arrive', audio.last - t0 > 0, 'watchdog fed')

    audio.command('pause')
    time.sleep(.2)
    audio.command('seek 158.7')
    time.sleep(.4)
    check('seek lands while paused', abs(audio.state['time'] - 158.7) < .2,
          f"{audio.state['time']:.3f}s")

    held = audio.state['time']
    time.sleep(.9)
    check('pause holds position', abs(audio.state['time'] - held) < .05, f'{held:.3f}s')
    check('pause clears playing', not audio.state['playing'])

    audio.command('play')
    time.sleep(.7)
    check('resume continues forward', audio.state['time'] > held + .3 and audio.state['playing'],
          f"{held:.3f}s -> {audio.state['time']:.3f}s")

    for level in (0., .5, 1., .75):
        audio.command(f'volume {level}')
    time.sleep(.2)
    check('volume commands accepted', not audio.error and audio.poll() is None, audio.error)

    audio.command(f'seek {duration + 50}')
    time.sleep(.3)
    check('seek past the end is clamped', audio.state['time'] <= duration,
          f"{audio.state['time']:.3f}s")

    audio.command('quit')
    try:
        audio.proc.wait(timeout=8)
        exited = True
    except Exception:
        audio.proc.kill()
        exited = False
    check('engine exits on quit', exited, f'code {audio.proc.returncode}')
    probe = work / 'released.mp3'
    try:
        copy.rename(probe)              # blocked while the engine still holds the file
        released = True
    except OSError as error:
        released = False
        print('  file still open:', error)
    check('mp3 handle released', released)
    check('no error reported', not audio.error, audio.error)

    print(f'\ntemp files left in {work} (Windows clears TEMP automatically)')
    print('ALL PASS' if not failures else 'FAILED: ' + ', '.join(failures))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
