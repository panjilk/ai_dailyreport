param(
    [string]$InputFile,
    [ValidateRange(1,120)][int]$Hours = 120,
    [ValidateRange(5,12)][int]$Limit = 10,
    [ValidateSet('auto','edge','sapi')][string]$Tts = 'auto',
    [Nullable[int]]$Rate,
    [ValidateRange(-20,20)][Nullable[int]]$Pitch,
    [switch]$CollectOnly,
    [switch]$Open
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { throw 'Python 3.10+ is required. Install Python and add it to PATH.' }
    & $py.Source -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the local Python environment.' }
}
& $pythonPath -c 'import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(m) for m in sys.argv[1:]) else 1)' PIL requests feedparser imageio_ffmpeg edge_tts bs4
if ($LASTEXITCODE -ne 0) {
    & $pythonPath -m pip --isolated --no-input install --keyring-provider disabled --disable-pip-version-check --no-cache-dir --timeout 20 --retries 1 --index-url https://pypi.org/simple -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check your internet connection.' }
}
$cliArgs = @('-m','dailyreport','--hours',"$Hours",'--limit',"$Limit",'--tts',$Tts)
if ($InputFile) { $cliArgs += @('--input',$InputFile) }
if ($null -ne $Rate) { $cliArgs += @('--rate',"$Rate") }
if ($null -ne $Pitch) { $cliArgs += @('--pitch',"$Pitch") }
if ($CollectOnly) { $cliArgs += '--collect-only' }
if ($Open) { $cliArgs += '--open' }
& $pythonPath @cliArgs
if ($LASTEXITCODE -ne 0) { throw 'The report could not be generated. See the message above.' }
