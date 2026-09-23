"""
Main Entrypoint for Windows PC Screen Server.
Initializes ADB port forwarding, validates display monitors, and starts the server.
"""

import sys
import os
import argparse
import asyncio
import subprocess
import shutil
import logging

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from vdd_manager import VDDManager
from stream_server import StreamServer, is_port_available, find_available_port
from discovery import DiscoveryServer, get_local_ip_addresses

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

def find_adb():
    """Locate adb executable in PATH or standard installation paths."""
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

def setup_adb_forwarding(port=8080):
    """Executes 'adb forward' to tunnel the USB connection to the phone."""
    adb = find_adb()
    if not adb:
        logging.warning("adb executable not found. Ensure Android SDK platform-tools is installed.")
        return False

    try:
        devices_out = subprocess.check_output([adb, "devices"], text=True)
        lines = [line.strip() for line in devices_out.splitlines() if line.strip()]
        # Skip header 'List of devices attached'
        connected = [l for l in lines[1:] if "device" in l and not "offline" in l and not "unauthorized" in l]

        if not connected:
            logging.warning("No Android device detected over USB.")
            logging.info("--> Please connect your phone via USB and enable 'USB Debugging' in Developer Options.")
            return False

        logging.info(f"Detected Android device(s): {len(connected)}")
        for dev in connected:
            logging.info(f"  * {dev}")

        # Set up port forwarding
        subprocess.run([adb, "forward", f"tcp:{port}", f"tcp:{port}"], check=True)
        # Also setup reverse in case client connects via reverse
        subprocess.run([adb, "reverse", f"tcp:{port}", f"tcp:{port}"], check=False)
        logging.info(f"Successfully configured USB port forwarding for port {port} (adb forward & reverse).")
        return True
    except Exception as e:
        logging.error(f"Error configuring ADB forwarding: {e}")
        return False

def print_banner():
    banner = r"""
===================================================================
      USB SECOND DISPLAY FOR WINDOWS - PC SERVER
===================================================================
[*] Biến điện thoại Android thành màn hình phụ thứ 2 qua cáp USB
[*] Hỗ trợ 60 FPS, độ trễ cực thấp, cảm ứng trực tiếp về PC
===================================================================
    """
    print(banner)

def main():
    print_banner()
    parser = argparse.ArgumentParser(description="USB Second Monitor PC Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--monitor", type=int, default=2, help="Monitor index to capture (1=Primary, 2=Secondary/Virtual)")
    parser.add_argument("--fps", type=int, default=60, help="Target FPS (default: 60)")
    parser.add_argument("--quality", type=int, default=70, help="JPEG quality 20-100 (default: 70)")
    parser.add_argument("--scale", type=float, default=1.0, help="Screen scale 0.5 - 1.0 (default: 1.0)")
    parser.add_argument("--enable-vdd", action="store_true", help="Download and activate Virtual Display Driver")
    parser.add_argument("--cli", action="store_true", help="Launch interactive CLI menu application")
    args = parser.parse_args()

    if args.cli:
        from cli import ServerCLI
        app = ServerCLI()
        app.main_loop()
        return

    # Check monitors
    display_count = VDDManager.get_display_count()
    logging.info(f"Windows currently detects {display_count} monitor(s).")

    if args.enable_vdd:
        logging.info("Requesting activation of Virtual Display Driver...")
        ok, res = VDDManager.enable_virtual_monitor()
        logging.info(f"Virtual Display activation: {ok} -> {res}")
        display_count = VDDManager.get_display_count()
        logging.info(f"Updated monitor count: {display_count}")

    if display_count < 2 and args.monitor == 2:
        logging.warning("=" * 65)
        logging.warning("HIỆN TẠI WINDOWS CHỈ CÓ 1 MÀN HÌNH CHÍNH!")
        logging.warning("Để dùng làm màn hình thứ 2 độc lập (Extend Desktop):")
        logging.warning("  1. Chạy lại với cờ: python main.py --enable-vdd")
        logging.warning("     (Hoặc chạy script scripts/setup_virtual_display.bat)")
        logging.warning("  2. Hoặc cắm Dummy HDMI / DisplayPort ảo.")
        logging.warning("Server sẽ tạm thời chuyển sang Monitor 1 (Mirror màn hình chính).")
        logging.warning("=" * 65)
        monitor_target = 1
    else:
        monitor_target = args.monitor

    # Check port availability
    if not is_port_available(args.port):
        if args.port == 8080:
            fallback = find_available_port(8080)
            logging.warning(f"Port 8080 is unavailable (occupied or forbidden). Automatically switching to port {fallback}.")
            args.port = fallback
        else:
            logging.error(f"Port {args.port} is currently unavailable. Please specify a different port with --port <number>.")
            sys.exit(1)

    # Set up ADB
    setup_adb_forwarding(port=args.port)

    # Local Wi-Fi / LAN IP addresses
    local_ips = get_local_ip_addresses()
    print("\n" + "=" * 65)
    print("  PHƯƠNG THỨC KẾT NỐI CHO ĐIỆN THOẠI:")
    print("  [1] CÁP USB (Khuyên dùng - Mượt nhất):")
    print(f"      Địa chỉ: ws://127.0.0.1:{args.port}")
    if local_ips:
        print("  [2] MẠNG KHÔNG DÂY WI-FI:")
        for ip in local_ips:
            print(f"      Địa chỉ: ws://{ip}:{args.port}")
        print("      (Hoặc bấm 'Tự động dò tìm' trên ứng dụng điện thoại)")
    print("=" * 65 + "\n")

    # Start Wi-Fi UDP Discovery service
    discovery = DiscoveryServer(ws_port=args.port)
    discovery.start()

    # Start WebSocket Server
    server = StreamServer(
        host="0.0.0.0",
        port=args.port,
        monitor_index=monitor_target,
        target_fps=args.fps
    )
    server.capture.set_quality(args.quality)
    server.capture.set_scale(args.scale)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logging.info("Server stopped by user.")
    finally:
        server.stop()
        discovery.stop()
        adb = find_adb()
        if adb:
            try:
                subprocess.run([adb, "forward", "--remove", f"tcp:{args.port}"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run([adb, "reverse", "--remove", f"tcp:{args.port}"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

if __name__ == "__main__":
    main()
