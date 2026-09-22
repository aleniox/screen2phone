@echo off
chcp 65001 > nul
title Kiem tra ket noi USB Dien thoai

echo ===================================================================
echo           KIỂM TRA KẾT NỐI CÁP USB ĐIỆN THOẠI ANDROID
echo ===================================================================
echo [*] Đang tìm kiếm thiết bị qua cáp USB...
echo.

:loop
for /f "skip=1 tokens=1,2" %%A in ('adb devices') do (
    if "%%B"=="device" (
        echo.
        echo ===================================================================
        echo [THÀNH CÔNG] ĐÃ PHÁT HIỆN ĐIỆN THOẠI: %%A
        echo [*] Đang thiết lập chuyển tiếp cổng USB 8080...
        adb forward tcp:8080 tcp:8080
        adb reverse tcp:8080 tcp:8080
        echo [HOÀN TẤT] Bây giờ bạn có thể bấm KẾT NỐI MÀN HÌNH trên điện thoại!
        echo ===================================================================
        pause
        exit /b
    )
    if "%%B"=="unauthorized" (
        echo [CẢNH BÁO] Điện thoại đã cắm nhưng CHƯA BẤM CHO PHÉP!
        echo --> Hãy mở màn hình điện thoại và bấm "Cho phép gỡ lỗi USB"!
    )
)

echo [!] Chưa nhận được điện thoại. Hãy đảm bảo:
echo     1. Đã cắm cáp USB (phải là cáp truyền được dữ liệu, không dùng cáp chỉ sạc).
echo     2. Điện thoại đã bật "Gỡ lỗi USB" (USB Debugging).
echo     3. Vuốt thông báo chọn chế độ "Truyền tệp" (File Transfer).
echo [*] Đang thử lại sau 3 giây... (Bấm Ctrl+C để thoát)
timeout /t 3 /nobreak > nul
goto loop
