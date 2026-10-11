"""Launch each delivered launcher and show what processes appeared (visual check is
impossible while the display is off, so this proves the chain starts)."""
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PKG = 'C:\\Users\\happw\\Downloads\\world-execute-mv-windows\\world-execute-mv'
QUERY = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -in "
         "'WindowsTerminal.exe','python.exe','cmd.exe' } | ForEach-Object { "
         "'{0} ppid={1} {2}' -f $_.ProcessId, $_.ParentProcessId, $_.CommandLine }")


def tree():
    out = subprocess.run(['powershell', '-NoProfile', '-Command', QUERY],
                         capture_output=True, text=True, encoding='utf-8', errors='replace')
    return [line for line in out.stdout.splitlines()
            if 'world-execute' in line or 'player.cmd' in line or 'WindowsTerminal' in line]


for name in ('全屏播放.cmd', '运行单文件.cmd'):
    path = PKG + '\\' + name
    # DEVNULL everywhere: the player inherits these handles, and a pipe would stay
    # open (and block us) until the player exits.
    result = subprocess.run(['cmd', '/c', 'start', '', path], stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f'launched {name!r} rc={result.returncode}', flush=True)
    time.sleep(7)
    rows = tree()
    print('  matched processes:')
    for row in rows[:8]:
        print('   ', row[:170])
    if not rows:
        print('    (none)')
