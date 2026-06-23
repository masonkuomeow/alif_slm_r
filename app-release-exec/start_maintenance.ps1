$wd = 'C:\Users\mason\alif\alif_ml-embedded-evaluation-kit\tools\app-release-exec'
$exe = 'maintenance.exe'

# Kill any stale maintenance or app-write processes first
Get-Process | Where-Object { $_.ProcessName -match 'maintenance|app-write' } | Stop-Process -Force

# Start maintenance.exe in a visible window
$proc = Start-Process -FilePath $exe -WorkingDirectory $wd -PassThru

# Give the window time to appear and print prompts
Start-Sleep -Seconds 1

# Use WScript.Shell to send keystrokes to the window
$wshell = New-Object -ComObject WScript.Shell

# Try to activate the window (by process ID via AppActivate)
# If AppActivate by PID fails, we send keys anyway (they go to the foreground window)
Start-Sleep -Seconds 1
$wshell.AppActivate($proc.Id) | Out-Null

# Send "1" + Enter for "Device Control"
$wshell.SendKeys('1')
Start-Sleep -Milliseconds 500
$wshell.SendKeys('{ENTER}')

# Wait for sub-menu to appear
Start-Sleep -Seconds 1

# Send "1" + Enter for "Hard maintenance mode"
$wshell.SendKeys('1')
Start-Sleep -Milliseconds 500
$wshell.SendKeys('{ENTER}')

# Now the window should show "Waiting for Target..[RESET Platform]"
Write-Host "`n`n"
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host ">>> maintenance.exe is running in a visible window.       <<<" -ForegroundColor Yellow
Write-Host ">>> When you see '[RESET Platform]' in the window,         <<<" -ForegroundColor Yellow
Write-Host ">>> PLEASE PRESS THE RESET BUTTON ON YOUR ALIF BOARD NOW! <<<" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "`n`n"

# Wait for up to 40 seconds, then check if the process is still running
Start-Sleep -Seconds 40
if (-not $proc.HasExited) {
    Write-Host "The maintenance window is still open. You can close it manually if it did not connect."
    # Keep the window alive so the user can read output
} else {
    Write-Host "maintenance.exe has exited. Check its output window."
}
