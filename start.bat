@echo off
REM Quick launcher — delegates to PowerShell script
powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
