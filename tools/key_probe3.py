"""Probe v3: log what player.Keys decodes for each key press, in a real terminal.

    py tools/key_probe3.py
Press the keys under test, then read keylog3.txt.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
import player  # noqa: E402

LOG = Path(__file__).with_name('keylog3.txt')
SECONDS = 120


def main():
    log = LOG.open('w', encoding='utf-8')
    start = time.monotonic()
    keys = player.Keys(sys.stdin)

    def say(text):
        log.write(f'{time.monotonic() - start:7.3f}  {text}\n')
        log.flush()
        print(text, flush=True)

    say(f'python {sys.version.split()[0]}  player.Keys  backend={"windows" if player.IS_WINDOWS else "posix"}')
    say(f'decoding for {SECONDS}s - press the keys now')
    deadline = time.monotonic() + SECONDS
    while time.monotonic() < deadline:
        if keys.pending(.05):
            decoded = keys.read()
            if decoded:
                say(f'decoded {decoded!r}')
    say('done')


if __name__ == '__main__':
    main()
