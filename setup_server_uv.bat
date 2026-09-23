@echo off
chcp 65001 >nul
title Cài đặt Second Screen Server với UV

echo ===================================================================
echo        CÀI ĐẶT MÔI TRƯỜNG SECOND SCREEN SERVER (UV)
echo ===================================================================
echo.

:: 1. Kiểm tra uv đã có trên máy chưa
set UV_CMD=""
where uv.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set UV_CMD=uv
) else (
    if exist "%USERPROFILE%\.local\bin\uv.exe" (
        set UV_CMD="%USERPROFILE%\.local\bin\uv.exe"
    ) else if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
        set UV_CMD="%USERPROFILE%\.cargo\bin\uv.exe"
    )
)

if %UV_CMD%=="" (
    echo [!] Chưa tìm thấy công cụ 'uv' trên hệ thống.
    echo [*] Đang tự động tải và cài đặt uv thông qua Astral Installer...
    echo.
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    
    :: Kiểm tra lại sau khi cài đặt
    if exist "%USERPROFILE%\.local\bin\uv.exe" (
        set UV_CMD="%USERPROFILE%\.local\bin\uv.exe"
    ) else if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
        set UV_CMD="%USERPROFILE%\.cargo\bin\uv.exe"
    ) else (
        echo.
        echo [X] Cài đặt uv thất bại hoặc chưa được thêm vào PATH.
        echo Vui lòng khởi động lại terminal hoặc cài đặt uv thủ công: https://docs.astral.sh/uv/
        pause
        exit /b 1
    )
)

echo [OK] Tìm thấy công cụ uv: %UV_CMD%
%UV_CMD% --version
echo.

:: Chuyển vào thư mục server
cd /d "%~dp0server"

:: 2. Khởi tạo virtual environment
echo [*] Đang khởi tạo môi trường ảo Python (.venv) với uv...
set UV_LINK_MODE=copy
%UV_CMD% venv
if %ERRORLEVEL% NEQ 0 (
    echo [X] Lỗi khi tạo virtual environment với uv!
    pause
    exit /b 1
)

:: 3. Cài đặt các thư viện cần thiết
echo.
echo [*] Đang cài đặt các thư viện từ requirements.txt...
%UV_CMD% pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [X] Lỗi khi cài đặt thư viện!
    pause
    exit /b 1
)

:: 4. Kiểm tra các thư viện đã cài đặt
echo.
echo [*] Kiểm tra môi trường và các thư viện...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import mss, PIL, win32api, websockets; print('[OK] Tất cả thư viện đã sẵn sàng!')"
) else (
    %UV_CMD% run python -c "import mss, PIL, win32api, websockets; print('[OK] Tất cả thư viện đã sẵn sàng!')"
)

echo.
echo ===================================================================
echo [THÀNH CÔNG] Môi trường Second Screen Server đã được cài đặt hoàn tất!
echo ===================================================================
echo.
echo Bạn có thể khởi động server bất kỳ lúc nào bằng file: Start_Server.bat
echo.

set /p START_NOW="Bạn có muốn khởi động Server ngay bây giờ không? (Y/N, mặc định Y): "
if /i "%START_NOW%"=="N" goto :END

echo [*] Đang khởi động Second Screen Server...
cd /d "%~dp0"
call Start_Server.bat

:END
exit /b 0
