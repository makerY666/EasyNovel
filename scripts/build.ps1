param([switch]$BackendOnly)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location $taskRoot
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (!(Test-Path $taskPython)) { throw 'Run scripts/setup.ps1 first.' }
& $taskPython -m pytest
if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
& $taskPython -m PyInstaller --noconfirm --clean --onefile --name easynovel-backend-x86_64-pc-windows-msvc --distpath apps/desktop/src-tauri/binaries --workpath artifacts/pyinstaller --specpath artifacts --paths $taskRoot --add-data "$taskRoot\alembic.ini;." --add-data "$taskRoot\migrations;migrations" --collect-submodules easynovel --collect-submodules langgraph.checkpoint.sqlite --collect-submodules keyring.backends --collect-data jieba --collect-all lancedb --collect-all pyarrow scripts/backend_entry.py
if ($LASTEXITCODE -ne 0) { throw 'Backend packaging failed.' }
if ($BackendOnly) { return }
npm.cmd --prefix apps/web ci
if ($LASTEXITCODE -ne 0) { throw 'Frontend dependencies failed.' }
npm.cmd --prefix apps/web test -- --run
if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed.' }
npm.cmd --prefix apps/desktop ci
if ($LASTEXITCODE -ne 0) { throw 'Desktop dependencies failed.' }
Push-Location apps/desktop
try { npm.cmd run build; if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed. Install the MSVC Rust toolchain and Visual Studio C++ build tools.' } }
finally { Pop-Location }
