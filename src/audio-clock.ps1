# audio-clock.ps1 - Windows audio engine for the world.execute(me); terminal MV.
#
# Plays the MP3 through Media Foundation (System.Windows.Media.MediaPlayer) and
# speaks the same line-oriented JSON protocol as the macOS audio-clock binary:
#
#   stdout ->  {"time":12.34,"duration":211.9,"playing":true}   clock update
#              {"error":"..."}                                 fatal note
#   stdin  ->  play | pause | seek <seconds> | volume <0..1> | quit
#
# The loop must never block: WPF only advances MediaPlayer.Position while the
# thread is pumping, so standard input is polled with a non-blocking async read
# (Task.Wait on a pipe would park the thread until the next command arrives).
#
# Kept 100% ASCII: Windows PowerShell 5.1 misreads non-ASCII bytes in files saved
# without a BOM. The player owns every message that reaches the user.
param(
    [Parameter(Mandatory = $true)][string]$Path,
    [double]$Interval = 0.025
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName System.Windows.Forms

$script:clock = [System.Diagnostics.Stopwatch]::StartNew()

function Emit($object) {
    [Console]::Out.WriteLine((ConvertTo-Json -InputObject $object -Compress))
    [Console]::Out.Flush()
}

# Process pending Win32/WPF messages for a few milliseconds.
function Pump([int]$milliseconds) {
    $until = $script:clock.Elapsed.TotalMilliseconds + $milliseconds
    while ($script:clock.Elapsed.TotalMilliseconds -lt $until) {
        [System.Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds 2
    }
}

function Parse-Number([string]$text) {
    $value = 0.0
    if ([double]::TryParse($text, [Globalization.NumberStyles]::Float,
            [Globalization.CultureInfo]::InvariantCulture, [ref]$value)) { return $value }
    return $null
}

if (-not (Test-Path -LiteralPath $Path)) { Emit @{ error = "audio file not found: $Path" }; exit 1 }
$resolved = (Resolve-Path -LiteralPath $Path).ProviderPath
if ($resolved -notmatch '^[A-Za-z]:\\[^"|\r\n]*$' -or $resolved.Length -gt 240) {
    # WPF turns the path into a URI; odd or very long paths are the usual failure mode.
    Emit @{ error = "path is not usable by Media Foundation: $resolved" }
    exit 1
}

$script:natural = 0.0
$script:playing = $false
$script:atEnd = $false
$script:failed = $null
$uri = New-Object System.Uri($resolved)

$player = New-Object System.Windows.Media.MediaPlayer
$player.Add_MediaOpened({
        param($sender, $e)
        if ($sender.NaturalDuration.HasTimeSpan) {
            $script:natural = $sender.NaturalDuration.TimeSpan.TotalSeconds
        }
    })
$player.Add_MediaEnded({
        # Reported as the end of the track; the player decides what happens next.
        $script:playing = $false
        $script:atEnd = $true
        Emit @{ time = $script:natural; duration = $script:natural; playing = $false }
    })
$player.Add_MediaFailed({
        param($sender, $e)
        $script:failed = $e.ErrorException.Message
    })

function Report {
    Emit @{ time = $script:player.Position.TotalSeconds; duration = $script:natural; playing = $script:playing }
}
$script:player = $player

function Open-Media {
    $player.Close()
    $script:natural = 0.0
    $player.Open($uri)
    $script:atEnd = $false
    $until = $script:clock.Elapsed.TotalMilliseconds + 15000
    while ($script:natural -le 0 -and $script:clock.Elapsed.TotalMilliseconds -lt $until) {
        Pump 20
        if ($script:failed) { Emit @{ error = ('media failed: ' + $script:failed) }; exit 1 }
    }
    if ($script:natural -le 0) { Emit @{ error = 'media open timed out' }; exit 1 }
}

function Handle-Command([string]$line) {
    $parts = $line.Trim() -split '\s+'
    switch ($parts[0].ToLowerInvariant()) {
        'play' {
            if ($script:atEnd) { Open-Media; $player.Position = [TimeSpan]::Zero }
            $player.Play()
            $script:playing = $true
            return $false
        }
        'pause' {
            if ($script:playing) { $player.Pause() }
            $script:playing = $false
            return $false
        }
        'seek' {
            $seconds = Parse-Number $parts[1]
            if ($null -ne $seconds) {
                if ($script:atEnd) { Open-Media }
                $clamped = [Math]::Min([Math]::Max(0.0, $seconds), [Math]::Max(0.0, $script:natural - 0.01))
                $player.Position = [TimeSpan]::FromSeconds($clamped)
                Report
            }
            return $false
        }
        'volume' {
            $level = Parse-Number $parts[1]
            if ($null -ne $level) { $player.Volume = [Math]::Min(1.0, [Math]::Max(0.0, $level)) }
            return $false
        }
        'quit' { return $true }
        default { return $false }
    }
}

Open-Media
$player.Volume = 1.0
Emit @{ time = 0.0; duration = $script:natural; playing = $false }

$stdin = [Console]::OpenStandardInput()
$buffer = New-Object byte[] 1024
$pending = $stdin.BeginRead($buffer, 0, $buffer.Length, $null, $null)
$text = ''
$done = $false
$next = $script:clock.Elapsed.TotalMilliseconds
while (-not $done) {
    if ($pending.AsyncWaitHandle.WaitOne(0)) {
        $count = $stdin.EndRead($pending)
        $pending = $null
        if ($count -le 0) {
            $done = $true                       # the player closed the pipe
        }
        else {
            $text += [Text.Encoding]::ASCII.GetString($buffer, 0, $count)
            while ($text.Contains("`n")) {
                $index = $text.IndexOf("`n")
                $line = $text.Substring(0, $index).Trim()
                $text = $text.Substring($index + 1)
                if ($line) { $done = Handle-Command $line }
                if ($done) { break }
            }
            if (-not $done) {
                $pending = $stdin.BeginRead($buffer, 0, $buffer.Length, $null, $null)
            }
        }
    }
    Pump 5
    $now = $script:clock.Elapsed.TotalMilliseconds
    if (($now - $next) -ge ($Interval * 1000)) {
        $next = $now
        Report
        if ($script:failed) { Emit @{ error = ('media failed: ' + $script:failed) }; $done = $true }
    }
}

$player.Stop()
$player.Close()
