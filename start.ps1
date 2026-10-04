param([switch]$Development)
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskExe=Join-Path $taskRoot 'apps\desktop\src-tauri\target\release\easynovel.exe'
if (!$Development -and (Test-Path -LiteralPath $taskExe)) {
    Start-Process -FilePath $taskExe -WorkingDirectory $taskRoot
    return
}
if (!$Development) { throw 'Build or install the desktop release first. For development use ./start.ps1 -Development.' }
if (!(Test-Path -LiteralPath (Join-Path $taskRoot '.venv\Scripts\python.exe'))) { throw 'Run scripts/setup.ps1 first.' }
Set-Location $taskRoot
if (!(Test-Path -LiteralPath (Join-Path $taskRoot 'apps\desktop\src-tauri\binaries\easynovel-backend-x86_64-pc-windows-msvc.exe'))) {
    & "$taskRoot\scripts\build.ps1" -BackendOnly
}
Push-Location apps/desktop
try { npm.cmd run dev; if ($LASTEXITCODE -ne 0) { throw 'Desktop development startup failed.' } }
finally { Pop-Location }
