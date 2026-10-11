param(
    [string]$Report,
    [switch]$Once
)
$ErrorActionPreference = 'Stop'
$ReportsRoot = Join-Path $PSScriptRoot 'reports\browser'
if (-not $Report) {
    $Latest = Get-ChildItem -LiteralPath $ReportsRoot -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'progress.json') } |
        Sort-Object Name -Descending | Select-Object -First 1
    if (-not $Latest) { throw 'No browser progress report found.' }
    $Report = $Latest.FullName
}
$Report = (Resolve-Path -LiteralPath $Report).Path
Write-Host "Observing $Report (Ctrl+C to stop)."
Write-Host 'Reads existing evidence only. Progress is sampled about every 10 seconds; saved images are not live video.'
$LastUpdate = $null
do {
    $ProgressPath = Join-Path $Report 'progress.json'
    try {
        $ProgressFile = Get-Item -LiteralPath $ProgressPath
        $Progress = Get-Content -LiteralPath $ProgressPath -Raw | ConvertFrom-Json
        if ($ProgressFile.LastWriteTimeUtc -ne $LastUpdate -or $Once) {
            $LastUpdate = $ProgressFile.LastWriteTimeUtc
            $Sample = @($Progress.samples) | Select-Object -Last 1
            $Age = [math]::Round(((Get-Date).ToUniversalTime() - $LastUpdate).TotalSeconds)
            Write-Host ("{0}  state={1}  presentations={2}  elapsed={3}s  update age={4}s" -f
                $LastUpdate.ToLocalTime().ToString('HH:mm:ss'), $Progress.state,
                $Progress.frames, [math]::Round($Sample.elapsedSeconds), $Age)
            $Image = Get-ChildItem -LiteralPath $Report -Filter '*.png' -File |
                Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
            if ($Image) { Write-Host "Latest saved image: $($Image.FullName)" }
        }
    } catch {
        Write-Host "Progress temporarily unavailable: $($_.Exception.Message)"
    }
    if (Test-Path -LiteralPath (Join-Path $Report 'result.json')) {
        Write-Host 'Capture finished; result.json is available.'
        break
    }
    if (-not $Once) { Start-Sleep -Seconds 2 }
} while (-not $Once)
