#!/usr/bin/env python3
"""Unit test for the Windows key decoder: lead byte + scan code, and raw VT input.

    python tests/test_keys.py

The console hands navigation keys over as two characters (a lead byte and a scan
code letter) and kbhit() cannot be used to wait for the second one. This pins
down every representation seen in the wild, plus the plain-key and Escape paths.
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
import player  # noqa: E402

failures = []


def check(label, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + label + ('  ' + detail if detail else ''))
    if not ok:
        failures.append(label)


def decode_with(chars, gap=.12):
    """Run player.Keys against a scripted character stream."""
    remaining = list(chars)

    class FakeMsvcrt:
        @staticmethod
        def getwch():
            if remaining:
                time.sleep(.001)
                return remaining.pop(0)
            time.sleep(gap)                      # idle: nothing pending
            raise OSError('no input')

    real = player.msvcrt
    player.msvcrt = FakeMsvcrt
    try:
        keys = player.Keys(None)
        time.sleep(.05)
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline and not remaining:
            if keys.pending(.01):
                return keys.read()
            time.sleep(.01)
        return ''
    finally:
        player.msvcrt = real


def main():
    cases = [
        ('right arrow, E0 lead', ('\xe0', 'M'), '\x1b[C'),
        ('left arrow, E0 lead', ('\xe0', 'K'), '\x1b[D'),
        ('up arrow, E0 lead', ('\xe0', 'H'), '\x1b[A'),
        ('down arrow, E0 lead', ('\xe0', 'P'), '\x1b[B'),
        ('right arrow, ESC lead', ('\x1b', 'M'), '\x1b[C'),
        ('left arrow, ESC lead', ('\x1b', 'K'), '\x1b[D'),
        ('right arrow, NUL lead', ('\x00', 'M'), '\x1b[C'),
        ('raw VT sequence', ('\x1b', '[', 'C'), '\x1b[C'),
        ('page up / page down', ('\x00', 'I'), '\x1b[5~'),
        ('plain letter', ('a',), 'a'),
        ('two letters', ('q', 'r'), 'qr'),
        ('lone Escape', ('\x1b',), '\x1b'),
        ('ctrl+c', ('\x03',), '\x03'),
        ('unknown extended key', ('\xe0', ';'), ''),
    ]
    for label, stream, expected in cases:
        got = decode_with(stream)
        check(label, got == expected, f'{got!r} (expected {expected!r})')
    print('ALL PASS' if not failures else 'FAILED: ' + ', '.join(failures))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
