$portName = 'COM3'
$baudRate = 115200
$timeoutSec = 30
$outputFile = 'C:\Users\mason\alif\alif_ml-embedded-evaluation-kit\tools\app-release-exec\com3_raw_output.txt'

# Kill any stale processes
Get-Process | Where-Object { $_.Name -match 'app-write|maintenance' } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

$port = $null
try {
    $port = [System.IO.Ports.SerialPort]::new($portName, $baudRate, 'None', 8, 'One')
    $port.ReadTimeout = 1000
    $port.Open()
    Write-Host "[OK] Opened $portName at $baudRate baud."
    Write-Host "[INFO] Press RESET on board NOW (or wait if already running)..."
    Write-Host "[INFO] Listening for $timeoutSec seconds..."
    Write-Host "---"

    $start = Get-Date
    $totalBytes = 0
    $stream = [System.IO.StreamWriter]::new($outputFile, $false, [System.Text.Encoding]::UTF8)

    while (((Get-Date) - $start).TotalSeconds -lt $timeoutSec) {
        try {
            $data = $port.ReadExisting()
            if ($data.Length -gt 0) {
                # Write live to console
                Write-Host -NoNewline $data
                # Write to file
                $stream.Write($data)
                $stream.Flush()
                $totalBytes += $data.Length
                $start = Get-Date  # Reset timeout on activity
            }
        } catch [System.TimeoutException] {
            # Normal, no data yet
        }
        Start-Sleep -Milliseconds 50
    }

    $stream.Close()
    $port.Close()

    Write-Host ""
    Write-Host "---"
    Write-Host "[INFO] Capture complete. Total chars received: $totalBytes"
    if ($totalBytes -eq 0) {
        Write-Host "[WARN] No data received. Possible causes:"
        Write-Host "  - SW4 is still set to 'SE' (should be 'U4' for app output)"
        Write-Host "  - Application does not print to UART"
        Write-Host "  - Wrong baud rate (tried $baudRate)"
    }
} catch {
    Write-Host "[ERROR] Failed to open $portName : $($_.Exception.Message)"
    if ($port -and $port.IsOpen) { $port.Close() }
}
