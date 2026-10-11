# Isolate how WPF MediaPlayer.Position advances under different pumps.
# powershell -NoProfile -Sta -File tools/pump_test.ps1 ; results in tools/pump-report.txt
param(
    [string]$Path = 'H:\mvport\src\media\song.mp3',
    [string]$Out = 'H:\mvport\tools\pump-report.txt'
)
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName System.Windows.Forms
$lines = New-Object System.Collections.ArrayList
function Say($text) { [void]$lines.Add($text); [Console]::Out.WriteLine($text); [Console]::Out.Flush() }

$script:opened = 0.0
function New-Player {
    $script:opened = 0.0
    $p = New-Object System.Windows.Media.MediaPlayer
    $p.Add_MediaOpened({ param($s, $e) $script:opened = $s.NaturalDuration.TimeSpan.TotalSeconds })
    $p.Add_MediaFailed({ param($s, $e) $script:opened = -1 })
    $p.Add_MediaEnded({ $script:ended = $true })
    $p.Open((New-Object System.Uri($Path)))
    $until = [Environment]::TickCount + 8000
    while ($script:opened -eq 0.0 -and [Environment]::TickCount -lt $until) { Start-Sleep -Milliseconds 20 }
    return $p
}
function Line($p) { return $p.Position.TotalSeconds }

Say "dotnet $([Environment]::Version.Major).$([Environment]::Version.Minor) apartment=$([Threading.Thread]::CurrentThread.GetApartmentState())"

# A: reproduce the one-liner that worked (sleep only)
$p = New-Player
Say "A opened=$($script:opened)"
$p.Volume = 0.03; $p.Position = [TimeSpan]::FromSeconds(20); $p.Play()
$a0 = Line $p; Start-Sleep -Milliseconds 1500; $a1 = Line $p
Say ("A sleep-only            {0:F3} -> {1:F3} (expect ~1.5 moved)" -f $a0, $a1)
$p.Stop(); $p.Close()

# B: DoEvents loop only
$p = New-Player
$p.Volume = 0.03; $p.Position = [TimeSpan]::FromSeconds(20); $p.Play()
$b0 = Line $p; $t0 = Get-Date; $n = 0
while (((Get-Date) - $t0).TotalSeconds -lt 1.5) { $null = [System.Windows.Forms.Application]::DoEvents(); $n++ }
$b1 = Line $p
Say ("B doevents-only         {0:F3} -> {1:F3} loops={2}" -f $b0, $b1, $n)
$p.Stop(); $p.Close()

# C: Task.Wait loop (what the engine does today)
$p = New-Player
$p.Volume = 0.03; $p.Position = [TimeSpan]::FromSeconds(20); $p.Play()
$c0 = Line $p; $t0 = Get-Date
while (((Get-Date) - $t0).TotalSeconds -lt 1.5) { $t = [Console]::In.ReadLineAsync(); $null = $t.Wait(10) }
$c1 = Line $p
Say ("C readlineasync-wait    {0:F3} -> {1:F3}" -f $c0, $c1)
$p.Stop(); $p.Close()

# D: DispatcherTimer inside Dispatcher.Run (canonical WPF pattern)
$script:p = New-Player
$script:p.Volume = 0.03; $script:p.Position = [TimeSpan]::FromSeconds(20); $script:p.Play()
$timer = New-Object System.Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromMilliseconds(50)
$timer.Add_Tick({
        if ($null -eq $script:d0) { $script:d0 = $script:p.Position.TotalSeconds }
        $script:d1 = $script:p.Position.TotalSeconds
    })
$timer.Start()
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$dispatcher = [System.Windows.Threading.Dispatcher]::CurrentDispatcher
$check = New-Object System.Windows.Threading.DispatcherTimer
$check.Interval = [TimeSpan]::FromMilliseconds(1500)
$check.Add_Tick({ $script:timer.Stop(); $script:check.Stop(); $dispatcher.Stop() })
$check.Start()
$dispatcher.Run()
$timer.Stop(); $check.Stop()
Say ("D dispatchertimer-run   {0:F3} -> {1:F3} over {2:F2}s" -f $script:d0, $script:d1, $stopwatch.Elapsed.TotalSeconds)
$script:p.Stop(); $script:p.Close()
Say 'finished'
