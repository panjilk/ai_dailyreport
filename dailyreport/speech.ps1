param([Parameter(Mandatory=$true)][string]$Manifest, [ValidateRange(-10,10)][int]$Rate = 2)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$jobs = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $voice = $synth.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'zh-CN' } | Select-Object -First 1
    if (-not $voice) { throw 'No installed zh-CN speech voice.' }
    $synth.SelectVoice($voice.VoiceInfo.Name)
    $synth.Rate = $Rate
    $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(24000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
    foreach ($job in $jobs) {
        $synth.SetOutputToWaveFile([string]$job.path, $format)
        $synth.Speak([string]$job.text)
        $synth.SetOutputToNull()
    }
    Write-Output $voice.VoiceInfo.Name
} finally {
    $synth.Dispose()
}
