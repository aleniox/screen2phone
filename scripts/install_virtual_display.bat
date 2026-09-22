@echo off
chcp 65001 > nul
title Cai dat va Bat Man Hinh Ao Thu 2 (Virtual Display)

:: Kiem tra quyen Administrator
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [THONG BAO] Dang yeu cau quyen Administrator de cai dat driver man hinh ao...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ===================================================================
echo     KICH HOAT MAN HINH PHU AO THU 2 TREN WINDOWS
echo ===================================================================
echo [*] Dang cai dat va bat man hinh ao...
echo.

cd /d "%~dp0\..\server\vdd_driver\usbmmidd_v2"

if not exist "deviceinstaller64.exe" (
    echo [!] Dang tai driver...
    cd /d "%~dp0\..\server"
    python -c "from vdd_manager import VDDManager; VDDManager.download_and_extract_driver()"
    cd /d "%~dp0\..\server\vdd_driver\usbmmidd_v2"
)

echo [*] Cai dat Driver vao he thong...
deviceinstaller64.exe install usbmmidd.inf usbmmidd

echo [*] Kich hoat Man Hinh Ao (Virtual Monitor #2)...
deviceinstaller64.exe enableidd 1

echo.
echo ===================================================================
echo [THANH CONG] Da tao xong Man Hinh Thu 2!
echo.
echo * Luu y:
echo   1. Nhan to hop phim [Windows + P] tren ban phim va chon [Extend] (Mo rong).
echo   2. Ban co the vao Windows Settings -> Display de sap xep vi tri man hinh.
echo ===================================================================
pause
