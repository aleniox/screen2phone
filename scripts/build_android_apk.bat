@echo off
chcp 65001 > nul
title Build Android APK - USB Second Screen

echo ===================================================================
echo     DANG BUILD FILE CAI DAT ANDROID APK (DEBUG/RELEASE)
echo ===================================================================
cd /d "%~dp0\..\client"

echo [*] Dang bien dich ung dung Flutter Android...
flutter build apk --debug

echo.
echo ===================================================================
if %ERRORLEVEL% EQU 0 (
    echo [THANH CONG] File APK da duoc tao tai:
    echo %~dp0\..\client\build\app\outputs\flutter-apk\app-debug.apk
    echo.
    echo Ban co the cai dat truc tiep bang lenh:
    echo adb install -r "%~dp0\..\client\build\app\outputs\flutter-apk\app-debug.apk"
) else (
    echo [THAT BAI] Khong the build APK. Vui long kiem tra Android SDK.
)
echo ===================================================================
pause
