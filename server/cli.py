"""
Interactive CLI Management Application for Second Screen Server.
Provides a user-friendly terminal interface to start/stop the server,
choose monitors, configure USB/ADB, and manage stream settings.
"""

import sys
import os
import time
import subprocess
import shutil
import asyncio
import threading
import logging

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Enable ANSI colors on Windows console
os.system('')

from discovery import DiscoveryServer, get_local_ip_addresses
from vdd_manager import VDDManager
from stream_server import StreamServer, is_port_available, find_available_port
import mss

# ANSI Colors
C_RESET   = "\033[0m"
C_BOLD    = "\033[1m"
C_DIM     = "\033[2m"
C_RED     = "\033[91m"
C_GREEN   = "\033[92m"
C_YELLOW  = "\033[93m"
C_BLUE    = "\033[94m"
C_MAGENTA = "\033[95m"
C_CYAN    = "\033[96m"
C_WHITE   = "\033[97m"
C_BG_BLUE = "\033[44m"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def find_adb():
    adb_path = shutil.which("adb")
    if adb_path:
        return adb_path
    candidates = [
        r"D:\Program\SDK\platform-tools\adb.exe",
        r"C:\Program Files\Android\platform-tools\adb.exe",
        os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def check_adb_status(port=8080):
    adb = find_adb()
    if not adb:
        return "Not Found", "Không tìm thấy adb.exe trong PATH hoặc Android SDK"
    try:
        out = subprocess.check_output([adb, "devices"], text=True, stderr=subprocess.STDOUT)
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        devices = [l for l in lines[1:] if "device" in l and "offline" not in l and "unauthorized" not in l]
        unauthorized = [l for l in lines[1:] if "unauthorized" in l]

        if unauthorized:
            return "Unauthorized", "Thiết bị chưa cho phép USB Debugging (hãy nhấn Cho phép trên màn hình điện thoại)"
        if not devices:
            return "No Device", "Chưa cắm cáp USB hoặc chưa bật Gỡ lỗi USB (Developer Options)"
        return "Connected", f"Đã nhận diện {len(devices)} thiết bị ({devices[0].split()[0]})"
    except Exception as e:
        return "Error", str(e)

def setup_usb_adb(port=8080):
    adb = find_adb()
    if not adb:
        print(f"{C_RED}[!] Không tìm thấy công cụ ADB.{C_RESET}")
        return False
    try:
        status, detail = check_adb_status(port)
        if status != "Connected":
            print(f"{C_YELLOW}[!] Trạng thái USB: {detail}{C_RESET}")
            return False
        subprocess.run([adb, "forward", f"tcp:{port}", f"tcp:{port}"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([adb, "reverse", f"tcp:{port}", f"tcp:{port}"], check=False, stdout=subprocess.DEVNULL)
        print(f"{C_GREEN}[OK] Đã kích hoạt ADB Port Forwarding & Reverse cho cổng {port}!{C_RESET}")
        return True
    except Exception as e:
        print(f"{C_RED}[!] Lỗi cấu hình ADB: {e}{C_RESET}")
        return False

def cleanup_usb_adb(port=8080):
    """Removes ADB port forwarding and reverse rules upon server shutdown."""
    adb = find_adb()
    if not adb:
        return
    try:
        subprocess.run([adb, "forward", "--remove", f"tcp:{port}"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([adb, "reverse", "--remove", f"tcp:{port}"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def get_monitors_info():
    with mss.mss() as sct:
        monitors = []
        for idx, m in enumerate(sct.monitors):
            if idx == 0:
                continue  # Index 0 is virtual union of all monitors
            is_pri = m.get('is_primary', False)
            w = m.get('width', 0)
            h = m.get('height', 0)
            monitors.append({
                'index': idx,
                'width': w,
                'height': h,
                'is_primary': is_pri,
                'name': m.get('name', f'Monitor {idx}')
            })
        return monitors

class ServerCLI:
    def __init__(self):
        default_port = 8080
        if is_port_available(default_port):
            self.port = default_port
            self.port_conflict_detected = False
        else:
            self.port = find_available_port(default_port)
            self.port_conflict_detected = True

        self.monitor_index = 2
        self.quality = 55
        self.scale = 0.8
        self.fps = 60
        self.server_task = None
        self.discovery = None
        self.stream_server = None
        self.is_running = False

    def print_banner(self):
        banner = f"""
{C_CYAN}{C_BOLD}=======================================================================
                    SECOND SCREEN SERVER - CLI
        Biến điện thoại Android thành màn hình phụ thứ 2 (PC)
======================================================================={C_RESET}"""
        print(banner)

    def print_status(self):
        monitors = get_monitors_info()
        local_ips = get_local_ip_addresses()
        adb_status, adb_detail = check_adb_status(self.port)

        # Ensure monitor_index is valid
        available_indices = [m['index'] for m in monitors]
        if self.monitor_index not in available_indices and monitors:
            self.monitor_index = available_indices[-1]

        print(f"{C_BOLD}--- TRANG THAI HE THONG ---{C_RESET}")
        # Server state
        if self.is_running:
            state_str = f"{C_GREEN}{C_BOLD}[RUNNING] DANG CHAY (Port {self.port}){C_RESET}"
        else:
            state_str = f"{C_YELLOW}[STOPPED] DA DUNG{C_RESET}"
        print(f"  Trang thai Server   : {state_str}")

        # Target Monitor
        cur_m = next((m for m in monitors if m['index'] == self.monitor_index), None)
        if cur_m:
            pri_tag = " (Man hinh chinh)" if cur_m['is_primary'] else " (Man hinh phu / Mo rong)"
            m_str = f"Man hinh {cur_m['index']} [{cur_m['width']}x{cur_m['height']}]{pri_tag}"
        else:
            m_str = f"Man hinh {self.monitor_index} (Chua nhan dien)"
        print(f"  Man hinh truyen     : {C_WHITE}{C_BOLD}{m_str}{C_RESET}")

        # Stream Config
        print(f"  Cau hinh truyen     : {C_WHITE}Chat luong: {self.quality}% | Ty le: {int(self.scale*100)}% | FPS: {self.fps}{C_RESET}")

        # Network & Port
        ip_str = ", ".join(local_ips) if local_ips else "Khong tim thay Wi-Fi/LAN"
        print(f"  Dia chi IP Wi-Fi    : {C_CYAN}{ip_str}{C_RESET}")
        port_note = ""
        if self.port_conflict_detected and self.port != 8080:
            port_note = f" {C_YELLOW}(Cổng 8080 bị chiếm bởi dịch vụ khác, tự động dùng {self.port}){C_RESET}"
        print(f"  Cổng kết nối (Port) : {C_CYAN}{self.port}{C_RESET}{port_note}")

        # USB ADB
        adb_color = C_GREEN if adb_status == "Connected" else (C_RED if adb_status == "Error" else C_YELLOW)
        print(f"  Ket noi Cap USB     : {adb_color}[{adb_status}] {adb_detail}{C_RESET}")
        print("-" * 71)

    def run_server_loop(self):
        if not is_port_available(self.port):
            clear_screen()
            self.print_banner()
            print(f"\n{C_RED}[!] Cổng {self.port} hiện đang bị chiếm dụng hoặc không có quyền truy cập.{C_RESET}")
            new_port = find_available_port(self.port)
            print(f"{C_CYAN}[*] Gợi ý cổng khả dụng: {new_port}{C_RESET}")
            ans = input(f"Bạn có muốn chuyển sang cổng {new_port} để chạy không? (Y/N, mặc định Y): ").strip().lower()
            if ans != 'n':
                self.port = new_port
                self.port_conflict_detected = True
            else:
                input("\nNhấn Enter để quay lại Menu chính...")
                return

        clear_screen()
        self.print_banner()
        print(f"\n{C_GREEN}{C_BOLD}>>> ĐANG KHỞI ĐỘNG SERVER TRÊN CỔNG {self.port}...<<<{C_RESET}\n")

        # Auto-configure ADB USB
        setup_usb_adb(self.port)

        # Start UDP Discovery
        self.discovery = DiscoveryServer(ws_port=self.port)
        self.discovery.start()

        # Start Stream Server
        self.stream_server = StreamServer(
            host="0.0.0.0",
            port=self.port,
            monitor_index=self.monitor_index,
            target_fps=self.fps
        )
        self.stream_server.capture.set_quality(self.quality)
        self.stream_server.capture.set_scale(self.scale)

        local_ips = get_local_ip_addresses()
        print(f"\n{C_CYAN}{C_BOLD}THÔNG TIN KẾT NỐI TRÊN ĐIỆN THOẠI:{C_RESET}")
        print(f"  {C_WHITE}1. Qua cáp USB (Khuyên dùng):{C_RESET} ws://127.0.0.1:{self.port}")
        if local_ips:
            print(f"  {C_WHITE}2. Qua Wi-Fi:{C_RESET}")
            for ip in local_ips:
                print(f"     - ws://{ip}:{self.port}")
            print(f"     {C_DIM}(Hoặc bấm 'Tự động dò tìm' trên app điện thoại){C_RESET}")

        print(f"\n{C_YELLOW}Nhấn {C_BOLD}[Ctrl + C]{C_RESET}{C_YELLOW} để dừng Server và quay lại Menu chính.{C_RESET}\n")

        self.is_running = True
        try:
            asyncio.run(self.stream_server.start())
        except KeyboardInterrupt:
            print(f"\n{C_YELLOW}[!] Đang dừng Server...{C_RESET}")
        except (OSError, PermissionError) as e:
            print(f"\n{C_RED}[!] Lỗi khởi động Server: {e}{C_RESET}")
            print(f"{C_YELLOW}[*] Cổng {self.port} đang bị hệ thống hoặc ứng dụng khác chiếm dụng (WinError 10013 / 10048).{C_RESET}")
            print(f"{C_CYAN}[*] Bạn có thể vào mục [7] trong Menu để đổi sang cổng khác (ví dụ 8082, 8088, 8888).{C_RESET}")
            input("\nNhấn Enter để quay lại Menu chính...")
        finally:
            if self.stream_server:
                self.stream_server.stop()
            if self.discovery:
                self.discovery.stop()
            cleanup_usb_adb(self.port)
            self.is_running = False
            print(f"{C_GREEN}[OK] Đã dừng Server và dọn dẹp kết nối thành công.{C_RESET}\n")
            time.sleep(1)

    def select_monitor_menu(self):
        clear_screen()
        self.print_banner()
        print(f"\n{C_BOLD}--- DANH SÁCH MÀN HÌNH HIỆN TẠI TRÊN WINDOWS ---{C_RESET}\n")
        monitors = get_monitors_info()
        for m in monitors:
            tag = f"{C_CYAN}(Màn hình chính - Primary){C_RESET}" if m['is_primary'] else f"{C_GREEN}(Màn hình phụ / Mở rộng - Extended){C_RESET}"
            selected = f" {C_YELLOW}<-- Dang chon{C_RESET}" if m['index'] == self.monitor_index else ""
            print(f"  [{m['index']}] Màn hình {m['index']}: {m['width']}x{m['height']} {tag}{selected}")

        print(f"\n  [V] Mở cài đặt hiển thị Windows (Win+P / Extend desktop)")
        print(f"  [0] Quay lại menu chính")

        choice = input(f"\n{C_BOLD}Chọn số màn hình muốn truyền (hoặc phím chức năng): {C_RESET}").strip()
        if choice == '0':
            return
        if choice.lower() == 'v':
            try:
                subprocess.Popen(["cmd", "/c", "start", "ms-settings:display"], shell=True)
            except Exception as e:
                print(f"Lỗi mở Settings: {e}")
            return

        try:
            val = int(choice)
            if any(m['index'] == val for m in monitors):
                self.monitor_index = val
                print(f"{C_GREEN}[OK] Đã đổi sang Màn hình {val}!{C_RESET}")
                time.sleep(0.8)
            else:
                print(f"{C_RED}[!] Màn hình không tồn tại.{C_RESET}")
                time.sleep(1)
        except ValueError:
            pass

    def select_preset_menu(self):
        clear_screen()
        self.print_banner()
        print(f"\n{C_BOLD}--- CẤU HÌNH ĐỘ NÉT & ĐỘ TRỄ ---{C_RESET}\n")
        print(f"  [1] Siêu mượt / Độ trễ thấp (Khuyên dùng) - Quality 55%, Scale 80%, 60 FPS")
        print(f"  [2] Cân bằng (Mặc định)                 - Quality 70%, Scale 85%, 60 FPS")
        print(f"  [3] Sắc nét cao (Ưu tiên đọc chữ/code)    - Quality 85%, Scale 100%, 45 FPS")
        print(f"  [4] Tùy chỉnh thông số thủ công")
        print(f"  [0] Quay lại")

        choice = input(f"\n{C_BOLD}Chọn cấu hình: {C_RESET}").strip()
        if choice == '1':
            self.quality = 55
            self.scale = 0.8
            self.fps = 60
            print(f"{C_GREEN}[OK] Đã chọn chế độ: Siêu mượt!{C_RESET}")
            time.sleep(0.8)
        elif choice == '2':
            self.quality = 70
            self.scale = 0.85
            self.fps = 60
            print(f"{C_GREEN}[OK] Đã chọn chế độ: Cân bằng!{C_RESET}")
            time.sleep(0.8)
        elif choice == '3':
            self.quality = 85
            self.scale = 1.0
            self.fps = 45
            print(f"{C_GREEN}[OK] Đã chọn chế độ: Sắc nét cao!{C_RESET}")
            time.sleep(0.8)
        elif choice == '4':
            try:
                q = int(input("Nhập Quality (20 - 100): ").strip() or self.quality)
                s = float(input("Nhập Scale (0.5 - 1.0): ").strip() or self.scale)
                f = int(input("Nhập FPS (15 - 60): ").strip() or self.fps)
                self.quality = max(20, min(100, q))
                self.scale = max(0.5, min(1.0, s))
                self.fps = max(15, min(60, f))
                print(f"{C_GREEN}[OK] Đã cập nhật tùy chỉnh thành công!{C_RESET}")
                time.sleep(0.8)
            except Exception as e:
                print(f"{C_RED}[!] Thông số không hợp lệ.{C_RESET}")
                time.sleep(1)

    def vdd_menu(self):
        clear_screen()
        self.print_banner()
        print(f"\n{C_BOLD}--- QUẢN LÝ MÀN HÌNH ẢO (VIRTUAL DISPLAY DRIVER - VDD) ---{C_RESET}\n")
        print(f"  Nếu máy tính của bạn chỉ có 1 màn hình và không có dây nối màn phụ,")
        print(f"  VDD sẽ tạo một màn hình ảo 1080p độc lập trong Windows Display Settings.\n")
        print(f"  [1] Kích hoạt Màn hình ảo (Enable Virtual Display)")
        print(f"  [2] Tắt Màn hình ảo (Disable Virtual Display)")
        print(f"  [0] Quay lại")

        choice = input(f"\n{C_BOLD}Chọn thao tác: {C_RESET}").strip()
        if choice == '1':
            print("Đang kích hoạt VDD...")
            ok, res = VDDManager.enable_virtual_monitor()
            if ok:
                print(f"{C_GREEN}[OK] Kích hoạt thành công: {res}{C_RESET}")
            else:
                print(f"{C_RED}[!] Không thể kích hoạt: {res}{C_RESET}")
            input("\nNhấn Enter để tiếp tục...")
        elif choice == '2':
            print("Đang tắt VDD...")
            ok, res = VDDManager.disable_virtual_monitor()
            if ok:
                print(f"{C_GREEN}[OK] Đã tắt màn hình ảo: {res}{C_RESET}")
            else:
                print(f"{C_RED}[!] Lỗi: {res}{C_RESET}")
            input("\nNhấn Enter để tiếp tục...")

    def change_port_menu(self):
        clear_screen()
        self.print_banner()
        print(f"\n{C_BOLD}--- CẤU HÌNH CỔNG KẾT NỐI (PORT) ---{C_RESET}\n")
        print(f"  Cổng WebSocket hiện tại: {C_CYAN}{self.port}{C_RESET}")
        status = f"{C_GREEN}[Khả dụng]{C_RESET}" if is_port_available(self.port) else f"{C_RED}[Đang bị chiếm / Không khả dụng]{C_RESET}"
        print(f"  Trạng thái             : {status}\n")
        suggested = find_available_port(self.port)
        if suggested != self.port:
            print(f"  Gợi ý cổng khả dụng    : {C_GREEN}{suggested}{C_RESET}\n")

        val = input(f"Nhập số cổng mới (1024-65535, Enter để giữ nguyên): ").strip()
        if not val:
            return
        try:
            p = int(val)
            if 1024 <= p <= 65535:
                if is_port_available(p):
                    self.port = p
                    self.port_conflict_detected = False
                    print(f"{C_GREEN}[OK] Đã đổi sang cổng {p}!{C_RESET}")
                else:
                    print(f"{C_YELLOW}[!] Cảnh báo: Cổng {p} có vẻ đang bị chiếm bởi một ứng dụng khác.{C_RESET}")
                    confirm = input("Bạn vẫn muốn dùng cổng này chứ? (Y/N): ").strip().lower()
                    if confirm == 'y':
                        self.port = p
            else:
                print(f"{C_RED}[!] Cổng phải nằm trong khoảng 1024 - 65535.{C_RESET}")
        except ValueError:
            print(f"{C_RED}[!] Vui lòng nhập số nguyên hợp lệ.{C_RESET}")
        time.sleep(1)

    def main_loop(self):
        while True:
            clear_screen()
            self.print_banner()
            self.print_status()

            print(f"{C_BOLD}--- MENU ĐIỀU KHIỂN ---{C_RESET}")
            print(f"  {C_GREEN}{C_BOLD}[1] Khởi động Server (Start Streaming){C_RESET}")
            print(f"  [2] Chọn Màn hình cần truyền (Hiện tại: Màn {self.monitor_index})")
            print(f"  [3] Cấu hình USB / ADB (Cổng {self.port})")
            print(f"  [4] Tùy chỉnh Độ nét & Độ trễ (Quality / Scale / FPS)")
            print(f"  [5] Quản lý Màn hình ảo VDD (Tạo thêm màn hình thứ 2)")
            print(f"  [6] Mở Windows Display Settings (Cài đặt màn hình / Win+P)")
            print(f"  [7] Đổi Cổng kết nối WebSocket (Hiện tại: Cổng {self.port})")
            print(f"  {C_RED}[0] Thoát{C_RESET}")

            choice = input(f"\n{C_BOLD}Nhập lựa chọn của bạn [0-7]: {C_RESET}").strip()

            if choice == '1':
                self.run_server_loop()
            elif choice == '2':
                self.select_monitor_menu()
            elif choice == '3':
                clear_screen()
                self.print_banner()
                print(f"\n{C_BOLD}--- KIỂM TRA & KÍCH HOẠT KẾT NỐI USB ADB ---{C_RESET}\n")
                setup_usb_adb(self.port)
                input(f"\nNhấn Enter để quay lại Menu chính...")
            elif choice == '4':
                self.select_preset_menu()
            elif choice == '5':
                self.vdd_menu()
            elif choice == '6':
                try:
                    subprocess.Popen(["cmd", "/c", "start", "ms-settings:display"], shell=True)
                    print(f"{C_GREEN}[OK] Đã mở Cài đặt màn hình Windows.{C_RESET}")
                    time.sleep(1)
                except Exception as e:
                    print(f"Lỗi: {e}")
            elif choice == '7':
                self.change_port_menu()
            elif choice == '0':
                clear_screen()
                print(f"\n{C_CYAN}Cảm ơn bạn đã sử dụng Second Screen Server! Tạm biệt.{C_RESET}\n")
                break

if __name__ == "__main__":
    app = ServerCLI()
    app.main_loop()
