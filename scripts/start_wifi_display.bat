@echo off
chcp 65001 > nul
title Second Screen Server (Ket noi Wi-Fi khong day)

echo ===================================================================
echo        SECOND SCREEN SERVER - KET NOI WI-FI KHONG DAY
echo ===================================================================
echo [*] Dang khoi dong Streaming Server cho mang Wi-Fi...
echo [*] Luu y: Dien thoai va may tinh phai ket noi vao cung mang Wi-Fi.
echo.

cd /d "%~dp0\..\server"
python main.py %*

pause
