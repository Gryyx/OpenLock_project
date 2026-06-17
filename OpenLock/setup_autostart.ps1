<#
.SYNOPSIS
    Registers screen_lock.py to run automatically whenever you log into Windows.

.DESCRIPTION
    Run this script ONCE (as Administrator) to set up auto-start.
    It creates a Windows Task Scheduler task that:
      - Triggers at user logon
      - Runs screen_lock.py silently in the background using pythonw.exe
      - Restarts automatically if it crashes
      - Keeps running indefinitely (no time limit)

.NOTES
    To remove the auto-start later, run:
        Unregister-ScheduledTask -TaskName "ScreenTimeLock" -Confirm:$false
#>

$TaskName = "ScreenTimeLock"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptPath = Join-Path $ScriptDir "screen_lock.py"

# Find pythonw.exe (runs Python without a visible console window).
# Falls back to python.exe if pythonw isn't found.
$PythonwPath = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonwPath) {
    $PythonwPath = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
}
if (-not $PythonwPath) {
    Write-Error "Could not find pythonw.exe or python.exe on PATH. Install Python and make sure it's on PATH, then re-run this script."
    exit 1
}

if (-not (Test-Path $ScriptPath)) {
    Write-Error "Could not find screen_lock.py at $ScriptPath. Place this setup script in the same folder as screen_lock.py."
    exit 1
}

Write-Host "Using Python at: $PythonwPath"
Write-Host "Target script:   $ScriptPath"

$Action = New-ScheduledTaskAction -Execute $PythonwPath -Argument "`"$ScriptPath`"" -WorkingDirectory $ScriptDir
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Run with highest privileges so the script can terminate other processes reliably.
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Runs screen_lock.py at logon to enforce app-blocking schedule." `
    -Force

Write-Host ""
Write-Host "Task '$TaskName' registered successfully."
Write-Host "It will start automatically the next time you log in."
Write-Host ""
Write-Host "To start it right now without rebooting, run:"
Write-Host "    Start-ScheduledTask -TaskName `"$TaskName`""
Write-Host ""
Write-Host "To remove auto-start later, run:"
Write-Host "    Unregister-ScheduledTask -TaskName `"$TaskName`" -Confirm:`$false"
