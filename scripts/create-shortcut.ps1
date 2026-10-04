$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskDesktop=[Environment]::GetFolderPath('Desktop')
$taskLinkPath=Join-Path $taskDesktop 'EasyNovel.lnk'
$taskShell=New-Object -ComObject WScript.Shell
$taskLink=$taskShell.CreateShortcut($taskLinkPath)
if ((Test-Path -LiteralPath $taskLinkPath) -and $taskLink.WorkingDirectory -ne $taskRoot) {
    $taskLinkPath=Join-Path $taskDesktop 'EasyNovel Workstation.lnk'
    if (Test-Path -LiteralPath $taskLinkPath) { throw 'A different shortcut already exists; leave it unchanged.' }
    $taskLink=$taskShell.CreateShortcut($taskLinkPath)
}
$taskLauncherName=([string][char]0x542f)+[char]0x52a8+'.cmd'
$taskLink.TargetPath=Join-Path $taskRoot $taskLauncherName
$taskLink.WorkingDirectory=$taskRoot
$taskLink.Description='EasyNovel local writing workstation'
$taskLink.IconLocation="$env:SystemRoot\System32\shell32.dll,70"
$taskLink.Save()
Write-Host "Shortcut created: $taskLinkPath"
