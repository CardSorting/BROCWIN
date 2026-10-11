# Local presentation narration only. Does not start or import the game runtime.
$ErrorActionPreference = 'Stop'
$sessionDirectory = [IO.Path]::GetFullPath($PSScriptRoot)
$utteranceFile = Join-Path $sessionDirectory 'utterances.json'
$utterances = Get-Content -Encoding UTF8 -LiteralPath $utteranceFile -Raw | ConvertFrom-Json
$audioDirectory = Join-Path $sessionDirectory 'audio'
[IO.Directory]::CreateDirectory($audioDirectory) | Out-Null
$speaker = New-Object -ComObject SAPI.SpVoice
$availableVoices = @($speaker.GetVoices())
$presenterVoice = $availableVoices | Where-Object { $_.GetDescription() -like '*David*' } | Select-Object -First 1
$audienceVoice = $availableVoices | Where-Object { $_.GetDescription() -like '*Zira*' } | Select-Object -First 1
if ($null -eq $presenterVoice -or $null -eq $audienceVoice) { throw 'Required local David and Zira voices were not found.' }
$speaker.Rate = 0
$speaker.Volume = 100
$completed = 0
foreach ($utterance in $utterances) {
    $outputPath = [IO.Path]::GetFullPath((Join-Path $sessionDirectory $utterance.wav))
    if (-not $outputPath.StartsWith($audioDirectory + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Audio output escapes presentation directory.' }
    if ($utterance.role -eq 'Audience') { $speaker.Voice = $audienceVoice } else { $speaker.Voice = $presenterVoice }
    $stream = New-Object -ComObject SAPI.SpFileStream
    try {
        # SAPI format 22: 22.05 kHz, 16-bit, mono. Files are verified before mixing.
        $stream.Format.Type = 22
        $stream.Open($outputPath, 3, $false)
        $speaker.AudioOutputStream = $stream
        [void]$speaker.Speak([string]$utterance.spokenText, 0)
    } finally {
        $stream.Close()
    }
    $completed += 1
    if (($completed % 15) -eq 0) { Write-Output "Synthesized $completed / $($utterances.Count) narration utterances" }
}
$record = [ordered]@{
    method = 'Local Windows SAPI synthesized narration; no cloud voice service'
    presenterVoice = $presenterVoice.GetDescription()
    audienceVoice = $audienceVoice.GetDescription()
    utterances = $utterances.Count
    rate = $speaker.Rate
    volume = $speaker.Volume
    voicesAreSynthesized = $true
    audienceIsSimulated = $true
    runtimeOrServiceLaunch = $false
}
$record | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $sessionDirectory 'speech-record.json')
Write-Output "Narration completed: $completed utterances"
