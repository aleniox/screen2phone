# Second Screen: Biến Điện Thoại Thành Màn Hình Phụ Cho Windows (USB & Wi-Fi)

Ứng dụng biến điện thoại thông minh Android thành màn hình phụ thứ 2 (Extended Display) cho máy tính Windows thông qua kết nối **Cáp USB** (độ trễ < 15ms) hoặc **Mạng Wi-Fi Không Dây** (tiện lợi, tự do di chuyển), hỗ trợ 60 FPS và cảm ứng trực tiếp về PC.

---

## Tính Năng Nổi Bật

- **Linh hoạt 2 chế độ**:
  - **Cáp USB**: Tốc độ 60 FPS, độ trễ siêu thấp (< 15ms), cắm là chạy qua ADB.
  - **Mạng Wi-Fi**: Kết nối không dây, tự động quét tìm máy tính trong mạng LAN (Auto-discovery), không cần cắm dây.
- **Màn hình thứ 2 thực thụ**: Windows nhận diện như một màn hình độc lập trong Display Settings, cho phép kéo thả bất kỳ cửa sổ, game, video sang điện thoại.
- **Cảm ứng ngược đa điểm (Touch Input)**:
  - 1 ngón chạm / di chuyển: Chuột trái & di chuột trên màn hình phụ.
  - Chạm giữ / kéo: Kéo thả cửa sổ, bôi đen văn bản.
  - 2 ngón chạm: Chuột phải.
  - 2 ngón vuốt lên/xuống: Cuộn trang (Mouse Wheel).
- **HUD Điều khiển nổi**: Tùy chỉnh nhanh độ phân giải, tỉ lệ nén ảnh, FPS mục tiêu (30/60) và xoay ngang/dọc linh hoạt.

---

## Cấu Trúc Dự Án

```
f:\screen\
├── server/                    # Máy chủ Windows (Python)
│   ├── main.py                # Điểm khởi chạy chính & tự động cấu hình ADB
│   ├── screen_capture.py      # Module chụp màn hình tốc độ cao (MSS & DXGI)
│   ├── stream_server.py       # WebSocket streaming server nhị phân
│   ├── input_handler.py       # Chuyển đổi cử chỉ chạm thành sự kiện chuột Windows
│   ├── vdd_manager.py         # Quản lý & kích hoạt màn hình ảo (IddCx)
│   └── requirements.txt
├── client/                    # Ứng dụng điện thoại (Flutter Android)
│   ├── lib/
│   │   ├── main.dart          # Giao diện chính & kết nối
│   │   ├── screens/display_screen.dart # Trình hiển thị toàn màn hình & cử chỉ
│   │   └── services/usb_stream_service.dart
│   └── pubspec.yaml
└── scripts/                   # Script tiện ích 1-Click
    ├── start_usb_display.bat  # 1-Click kết nối USB & chạy Server
    ├── install_virtual_display.bat # 1-Click kích hoạt màn hình ảo
    └── build_android_apk.bat  # Build file APK cài đặt lên điện thoại
```

---

## Hướng Dẫn Sử Dụng Nhanh (Quick Start)

### Bước 1: Chuẩn bị trên Điện thoại Android
1. Vào **Cài đặt (Settings)** > **Thông tin điện thoại (About Phone)** > Chạm liên tục 7 lần vào **Số bản dựng (Build Number)** để mở khóa *Tùy chọn nhà phát triển (Developer Options)*.
2. Vào **Cài đặt cho người phát triển**, bật mục **Gỡ lỗi USB (USB Debugging)**.
3. Cắm cáp USB nối điện thoại với máy tính.

### Bước 2: Tạo Màn Hình Ảo Thứ 2 Trên Windows (Chỉ cần làm 1 lần)
Nếu máy tính của bạn chưa có sẵn màn hình thứ 2 hoặc cổng cắm ảo:
- Nhấp đúp chuột vào file: `scripts\install_virtual_display.bat`
- Windows sẽ kích hoạt một màn hình ảo độc lập (Monitor 2).

---

## Cách Kết Nối Qua Wi-Fi (Không Dây)

1. Kết nối điện thoại và máy tính vào **CÙNG MỘT MẠNG WI-FI**.
2. Trên máy tính, nhấp đúp chuột chạy: `scripts\start_wifi_display.bat`.
   - Cửa sổ sẽ hiển thị địa chỉ IP nội bộ của máy tính (ví dụ: `ws://192.168.1.42:8080`).
3. Trên điện thoại:
   - Chuyển sang tab **Wi-Fi (Không Dây)**.
   - Bấm nút **"Tự động dò tìm máy tính"** để ứng dụng tự quét và tìm thấy máy tính trong mạng, sau đó bấm **Kết nối**.
   - Hoặc bạn có thể tự nhập địa chỉ IP hiển thị trên máy tính vào ô và bấm **KẾT NỐI MÀN HÌNH**.

