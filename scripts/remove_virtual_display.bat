@echo off
chcp 65001 > nul
title Tat Man Hinh Ao (Virtual Display)

:: Kiem tra quyen Administrator
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ===================================================================
echo               TAT MAN HINH AO TREN WINDOWS
echo ===================================================================
cd /d "%~dp0\..\server\vdd_driver\usbmmidd_v2"
deviceinstaller64.exe enableidd 0
echo [*] Da tat man hinh ao thanh cong!
pause
