@echo off
cd /d "%~dp0"
title EasyNovel
powershell.exe -NoProfile -File "%~dp0scripts\start-browser.ps1" -OpenBrowser
if errorlevel 1 (
  echo EasyNovel could not start. See the error above.
  pause
)
