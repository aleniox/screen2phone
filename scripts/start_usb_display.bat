@echo off
chcp 65001 > nul
title USB Second Screen Server - Khoi dong

echo ===================================================================
echo             USB SECOND SCREEN FOR WINDOWS
echo ===================================================================
echo [*] Dang kiem tra ket noi ADB va dien thoai qua cong USB...

set ADB_EXE=""
where adb.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set ADB_EXE="adb.exe"
) else (
    if exist "D:\Program\SDK\platform-tools\adb.exe" (
        set ADB_EXE="D:\Program\SDK\platform-tools\adb.exe"
    ) else if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" (
        set ADB_EXE="%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
    )
)

if %ADB_EXE%=="" (
    echo [CANH BAO] Khong tim thay cong cu adb.exe!
    echo Vui long cai dat Android SDK Platform Tools hoac them vao PATH.
) else (
    echo [*] Su dung ADB: %ADB_EXE%
    %ADB_EXE% devices
    echo [*] Thiet lap chuyen tiep cong USB (port 8080)...
    %ADB_EXE% forward tcp:8080 tcp:8080
    %ADB_EXE% reverse tcp:8080 tcp:8080
)

echo.
echo [*] Khoi dong Python Streaming Server tren Windows...
cd /d "%~dp0\..\server"
python main.py %*

pause
