"""Log what the console actually delivers for each key press.

Run inside a terminal window, press the keys under test, then read keylog.txt:

    py tools/key_probe.py

Raw msvcrt bytes are logged (before any translation), which is the ground truth
for the player's key layer.
"""
import msvcrt
import sys
import time
from pathlib import Path

LOG = Path(__file__).with_name('keylog.txt')
SECONDS = 120
NAMES = {0x4B: 'LEFT', 0x4D: 'RIGHT', 0x48: 'UP', 0x50: 'DOWN', 0x47: 'HOME',
         0x4F: 'END', 0x49: 'PGUP', 0x51: 'PGDN', 0x52: 'INS', 0x53: 'DEL'}


def main():
    log = LOG.open('w', encoding='utf-8')

    def say(text):
        log.write(text + '\n')
        log.flush()
        print(text, flush=True)

    say(f'python {sys.version.split()[0]}  pid {__import__("os").getpid()}')
    say(f'logging for {SECONDS}s -> press the keys now')
    deadline = time.time() + SECONDS
    while time.time() < deadline:
        if not msvcrt.kbhit():
            time.sleep(.004)
            continue
        char = msvcrt.getwch()
        if char in ('\xe0', '\x00'):
            first = 'E0' if char == '\xe0' else '00'
            started = time.time()
            while not msvcrt.kbhit() and time.time() - started < .5:
                time.sleep(.002)
            if msvcrt.kbhit():
                second = msvcrt.getwch()
                say(f'extended {first} + {second!r} (0x{ord(second):02X}) -> {NAMES.get(ord(second), "?")}'
                    f'  | player maps to {SKIP_IF_UNMAPPED(ord(second))}')
            else:
                say(f'extended {first} + (nothing arrived)')
        else:
            say(f'plain {char!r} (0x{ord(char):02X})')
    say('done')


def SKIP_IF_UNMAPPED(code):
    """Mirror of player.Keys.EXTENDED so the log shows what the player would see."""
    table = {'H': '\x1b[H', 'F': '\x1b[F', 'P': '\x1b[A', 'Q': '\x1b[B',
             'K': '\x1b[D', 'M': '\x1b[C', 'G': '\x1b[G'}
    return repr(table.get(chr(code), '(dropped)'))


if __name__ == '__main__':
    main()
