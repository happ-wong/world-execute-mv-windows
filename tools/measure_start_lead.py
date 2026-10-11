"""Measure how the audio clock behaves right after playback starts.

    python tools/measure_start_lead.py
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
import player  # noqa: E402


class Options:
    audio_latency = 0.0


def run_from(audio, target, seconds=2.0, volume=0.05):
    audio.command('pause')
    time.sleep(.15)
    audio.command(f'volume {volume}')
    audio.command(f'seek {target}')
    time.sleep(.25)
    before = audio.state['time']
    started = time.monotonic()
    audio.command('play')
    samples = []
    while time.monotonic() - started < seconds:
        time.sleep(.1)
        samples.append((time.monotonic() - started, audio.state['time']))
    print(f'seek {target:6.1f} -> paused clock {before:8.3f}')
    for wall, value in samples[:8]:
        print(f'   +{wall:4.2f}s  clock {value:8.3f}  lead {value - target - wall:+.3f}s')
    tail = samples[-1][1] - samples[8][1]
    span = samples[-1][0] - samples[8][0]
    print(f'   steady-state rate over the last {span:.1f}s: {tail / span:.4f}x\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', default=str(ROOT / 'src' / 'media' / 'song.mp3'))
    args = parser.parse_args()
    audio = player.make_audio(Options(), args.path)
    for target in (0., 5., 60., 158.7):
        run_from(audio, target)
    audio.command('quit')
    return 0


if __name__ == '__main__':
    sys.exit(main())
