"""Probe v2: read keys with a blocking reader thread (no kbhit gating).

    py tools/key_probe2.py
Logs every character msvcrt hands back, with timestamps, to keylog2.txt.
Press the arrow keys, then read the log.
"""
import msvcrt
import queue
import sys
import threading
import time
from pathlib import Path

LOG = Path(__file__).with_name('keylog2.txt')
SECONDS = 120


def main():
    log = LOG.open('w', encoding='utf-8')
    start = time.monotonic()
    chars = queue.Queue()

    def reader():
        while True:
            try:
                chars.put(msvcrt.getwch())
            except Exception as error:      # noqa: BLE001
                chars.put(f'<reader died: {error!r}>')
                return

    threading.Thread(target=reader, daemon=True).start()

    def say(text):
        log.write(f'{time.monotonic() - start:7.3f}  {text}\n')
        log.flush()
        print(text, flush=True)

    say(f'python {sys.version.split()[0]}  pid {__import__("os").getpid()}')
    say(f'blocking reader thread started; logging {SECONDS}s')
    deadline = time.monotonic() + SECONDS
    while time.monotonic() < deadline:
        try:
            char = chars.get(timeout=.1)
        except queue.Empty:
            continue
        say(f'char {char!r}  ord 0x{ord(char):02X}')
    say('done')


if __name__ == '__main__':
    main()
