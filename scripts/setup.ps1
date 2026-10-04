$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location $taskRoot
if (!(Test-Path .venv\Scripts\python.exe)) { py -3.12 -m venv .venv; if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 required for development.' } }
& .\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend installation failed.' }
npm.cmd --prefix apps/web ci
if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed.' }
npm.cmd --prefix apps/desktop ci
if ($LASTEXITCODE -ne 0) { throw 'Desktop installation failed.' }
