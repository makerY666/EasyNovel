param([ValidateRange(1024,65535)][int]$Port=8765, [ValidateRange(1024,65535)][int]$WebPort=5173, [switch]$OpenBrowser)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskPython=Join-Path $taskRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $taskPython)) { throw 'Run scripts/setup.ps1 first.' }
if (!(Test-Path -LiteralPath (Join-Path $taskRoot 'apps\web\node_modules'))) { throw 'Run scripts/setup.ps1 first.' }
$taskDataDir=if ($env:EASYNOVEL_DATA_DIR) { $env:EASYNOVEL_DATA_DIR } else { Join-Path $env:LOCALAPPDATA 'EasyNovel' }
$null=New-Item -ItemType Directory -Path $taskDataDir -Force
$taskDataDir=(Resolve-Path -LiteralPath $taskDataDir).Path
$taskSessionFile=Join-Path $taskDataDir 'browser-session.json'
$taskBackendFile=Join-Path $taskDataDir 'backend-session.json'
function Open-Workstation([string]$sessionToken,[int]$browserPort) {
    if ($OpenBrowser) { Start-Process "http://127.0.0.1:$browserPort/#session=$([Uri]::EscapeDataString($sessionToken))" }
}
function Get-ReadyBrowser {
    if (!(Test-Path -LiteralPath $taskSessionFile)) { return $null }
    try {
        $existing=Get-Content -LiteralPath $taskSessionFile -Raw | ConvertFrom-Json
        $health=Invoke-RestMethod -Uri "http://127.0.0.1:$($existing.port)/api/v1/health" -Headers @{Authorization="Bearer $($existing.token)"} -TimeoutSec 2
        if ($health.status -ne 'ok') { return $null }
        $webHealth=Invoke-RestMethod -Uri "http://127.0.0.1:$($existing.web_port)/api/v1/health" -Headers @{Authorization="Bearer $($existing.token)"} -TimeoutSec 2
        if ($webHealth.status -ne 'ok') { return $null }
        return $existing
    } catch { return $null }
}
function Get-FreePort([int]$preferred,[int]$excluded=0) {
    for ($candidate=$preferred;$candidate -le [Math]::Min(65535,$preferred+100);$candidate++) {
        if ($candidate -eq $excluded) { continue }
        $listener=New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback,$candidate)
        try { $listener.Start(); return $candidate } catch { } finally { $listener.Stop() }
    }
    throw 'No free local port was found. Close unused applications and try again.'
}
$taskHash=[System.Security.Cryptography.SHA256]::Create()
try { $taskIdentity=([BitConverter]::ToString($taskHash.ComputeHash([Text.Encoding]::UTF8.GetBytes($taskDataDir.ToLowerInvariant())))).Replace('-','') }
finally { $taskHash.Dispose() }
$taskMutex=New-Object System.Threading.Mutex($false,"Local\EasyNovel-$taskIdentity")
$taskOwnsMutex=$false
$taskProcess=$null
$taskOwnsBackend=$false
$taskWebProcess=$null
try {
    # Double clicks share the same data instance, even when its ports changed.
    for ($attempt=0;$attempt -lt 90;$attempt++) {
        $taskExisting=Get-ReadyBrowser
        if ($taskExisting) {
            Open-Workstation $taskExisting.token $taskExisting.web_port
            Write-Host 'EasyNovel is already running. Opened the existing workstation.'
            return
        }
        try { $taskOwnsMutex=$taskMutex.WaitOne(0) }
        catch [System.Threading.AbandonedMutexException] { $taskOwnsMutex=$true }
        if ($taskOwnsMutex) { break }
        Start-Sleep -Milliseconds 500
    }
    if (!$taskOwnsMutex) { throw 'EasyNovel is still starting. Please try again in a moment.' }
    $taskExisting=Get-ReadyBrowser
    if ($taskExisting) {
        Open-Workstation $taskExisting.token $taskExisting.web_port
        Write-Host 'EasyNovel is already running. Opened the existing workstation.'
        return
    }
    # A manually started backend can be reused without opening its database twice.
    if (Test-Path -LiteralPath $taskBackendFile) {
        try {
            $taskBackend=Get-Content -LiteralPath $taskBackendFile -Raw | ConvertFrom-Json
            $taskHealth=Invoke-RestMethod -Uri "http://127.0.0.1:$($taskBackend.port)/api/v1/health" -Headers @{Authorization="Bearer $($taskBackend.token)"} -TimeoutSec 2
            if ($taskHealth.status -eq 'ok') {
                $taskProcess=Get-Process -Id $taskBackend.pid -ErrorAction Stop
                $Port=[int]$taskBackend.port
                $env:EASYNOVEL_TOKEN=$taskBackend.token
            }
        } catch { $taskProcess=$null }
    }
    if (!$taskProcess) {
        $taskPreferredPort=$Port; $Port=Get-FreePort $Port
        if ($Port -ne $taskPreferredPort) { Write-Host "Local port $taskPreferredPort is busy; using $Port." }
        $taskBytes=New-Object byte[] 32
        $taskRandom=[System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $taskRandom.GetBytes($taskBytes) } finally { $taskRandom.Dispose() }
        $env:EASYNOVEL_TOKEN=[Convert]::ToBase64String($taskBytes)
        $taskProcess=Start-Process -FilePath $taskPython -ArgumentList @('-m','easynovel','--port',"$Port",'--data-dir',"`"$taskDataDir`"",'--parent-pid',"$PID") -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru
        $taskOwnsBackend=$true
    }
    $taskReady=$false
    for ($taskAttempt=0;$taskAttempt -lt 60;$taskAttempt++) {
        if ($taskProcess.HasExited) { throw 'Backend exited before startup. Another backend may already have this data open.' }
        try {
            $taskHealth=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/v1/health" -Headers @{Authorization="Bearer $env:EASYNOVEL_TOKEN"} -TimeoutSec 2
            $taskReady=($taskHealth.status -eq 'ok')
            if ($taskReady) { break }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    if (!$taskReady) { throw 'Backend startup timed out.' }
    $taskPreferredWebPort=$WebPort; $WebPort=Get-FreePort $WebPort $Port
    if ($WebPort -ne $taskPreferredWebPort) { Write-Host "Browser port $taskPreferredWebPort is busy; using $WebPort." }
    $env:EASYNOVEL_PROXY_TARGET="http://127.0.0.1:$Port"
    $taskNode=(Get-Command node.exe -ErrorAction Stop).Source
    $taskVite=Join-Path $taskRoot 'scripts\watch-vite.mjs'
    $taskWebProcess=Start-Process -FilePath $taskNode -ArgumentList @("`"$taskVite`"","$WebPort","$PID") -WorkingDirectory (Join-Path $taskRoot 'apps\web') -WindowStyle Hidden -PassThru
    $taskWebStarted=$false
    for ($taskAttempt=0;$taskAttempt -lt 60;$taskAttempt++) {
        if ($taskWebProcess.HasExited) { throw 'Web workstation exited before startup.' }
        try { $null=Invoke-WebRequest -Uri "http://127.0.0.1:$WebPort/" -UseBasicParsing -TimeoutSec 2; $taskWebStarted=$true; break }
        catch { Start-Sleep -Milliseconds 500 }
    }
    if (!$taskWebStarted) { throw 'Web workstation startup timed out.' }
    @{port=$Port; web_port=$WebPort; token=$env:EASYNOVEL_TOKEN; pid=$taskProcess.Id; web_pid=$taskWebProcess.Id; launcher_pid=$PID} | ConvertTo-Json | Set-Content -LiteralPath $taskSessionFile -Encoding UTF8
    Open-Workstation $env:EASYNOVEL_TOKEN $WebPort
    Write-Host "EasyNovel is ready: http://127.0.0.1:$WebPort/"
    Write-Host 'Keep this terminal open. Press Ctrl+C to stop EasyNovel safely.'
    while (!$taskProcess.HasExited -and !$taskWebProcess.HasExited) { Start-Sleep -Seconds 1 }
    if ($taskProcess.HasExited -and !$taskOwnsBackend) {
        Write-Host 'The connected backend has stopped.'
        return
    }
    if ($taskProcess.HasExited -and $taskProcess.ExitCode -eq 0) {
        Write-Host 'EasyNovel stopped safely.'
        return
    }
    throw 'A workstation service exited. Restart EasyNovel; saved work remains available.'
} finally {
    if ($taskProcess -and $taskOwnsBackend) {
        try { Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$Port/api/v1/shutdown" -Headers @{Authorization="Bearer $env:EASYNOVEL_TOKEN"} -TimeoutSec 3 | Out-Null } catch {}
        if (!$taskProcess.HasExited) { Stop-Process -Id $taskProcess.Id -ErrorAction SilentlyContinue }
    }
    if ($taskWebProcess) {
        if (!$taskWebProcess.HasExited) { Stop-Process -Id $taskWebProcess.Id -ErrorAction SilentlyContinue }
        if (Test-Path -LiteralPath $taskSessionFile) {
            try {
                $taskOwned=Get-Content -LiteralPath $taskSessionFile -Raw | ConvertFrom-Json
                if ($taskOwned.web_pid -eq $taskWebProcess.Id) { Remove-Item -LiteralPath $taskSessionFile -Force }
            } catch { }
        }
    }
    if ($taskOwnsMutex) { $taskMutex.ReleaseMutex() }
    $taskMutex.Dispose()
}
