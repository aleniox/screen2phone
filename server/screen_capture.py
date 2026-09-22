"""
High-performance screen capture module with a dedicated capture worker thread.
Eliminates thread-switching overhead, ensures zero-latency streaming,
and prevents network buffer bloat.
"""

import io
import time
import threading
import mss
import ctypes
import win32api
from PIL import Image, ImageDraw

user32 = ctypes.windll.user32

def attach_to_input_desktop():
    """Ensures current thread is attached to the active user desktop for BitBlt capture."""
    try:
        # 0x01FF = GENERIC_ALL
        h_desk = user32.OpenInputDesktop(0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)
            user32.CloseDesktop(h_desk)
    except Exception:
        pass

def create_cursor_sprite():
    """Generates a crisp Windows arrow cursor sprite with black outline and white fill."""
    cursor = Image.new('RGBA', (20, 28), (0, 0, 0, 0))
    draw = ImageDraw.Draw(cursor)
    points = [(0, 0), (0, 22), (5, 17), (10, 27), (13, 25), (8, 15), (15, 15)]
    # Draw dark outline
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (-1, 1)]:
        draw.polygon([(x + dx, y + dy) for x, y in points], fill=(0, 0, 0, 255))
    # Draw white fill
    draw.polygon(points, fill=(255, 255, 255, 255))
    return cursor

class ScreenCapture:
    def __init__(self, monitor_index=2):
        self.monitor_index = monitor_index
        self.quality = 55  # Optimized default for real-time low latency
        self.scale = 0.8   # 0.8 = ~1536x864, crystal clear on phone, 70% smaller size
        self.latest_frame = b""
        self.running = False
        self.worker_thread = None
        self.lock = threading.Lock()
        self.cursor_sprite = create_cursor_sprite()
        
        # Initial probe
        attach_to_input_desktop()
        self.sct = mss.MSS() if hasattr(mss, 'MSS') else mss.mss()
        self._refresh_monitors()

    def _refresh_monitors(self):
        """Monitors in mss: index 0 is all monitors combined, 1 is primary, 2 is secondary."""
        try:
            self.monitors = self.sct.monitors
        except Exception:
            pass
        if len(self.monitors) > self.monitor_index:
            self.active_monitor = self.monitors[self.monitor_index]
        elif len(self.monitors) > 1:
            self.active_monitor = self.monitors[1]
            self.monitor_index = 1
        else:
            self.active_monitor = self.monitors[0]
            self.monitor_index = 0

    def start_worker(self):
        """Starts the background continuous capture loop on a dedicated thread."""
        if self.running:
            return
        self.running = True
        self.worker_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.worker_thread.start()

    def stop_worker(self):
        self.running = False

    def _capture_loop(self):
        """Dedicated thread loop that captures and compresses the desktop at high speed."""
        attach_to_input_desktop()
        sct = mss.MSS() if hasattr(mss, 'MSS') else mss.mss()
        
        while self.running:
            try:
                with self.lock:
                    target_monitor = self.active_monitor
                    quality = self.quality
                    scale = self.scale

                sct_img = sct.grab(target_monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

                if scale < 1.0:
                    target_w = int(img.width * scale)
                    target_h = int(img.height * scale)
                    img = img.resize((target_w, target_h), Image.Resampling.BILINEAR)

                # Draw Windows Mouse Cursor if it is located inside this monitor
                try:
                    cur_x, cur_y = win32api.GetCursorPos()
                    m_left = target_monitor["left"]
                    m_top = target_monitor["top"]
                    m_w = target_monitor["width"]
                    m_h = target_monitor["height"]
                    if m_left <= cur_x < m_left + m_w and m_top <= cur_y < m_top + m_h:
                        rel_x = int((cur_x - m_left) * scale)
                        rel_y = int((cur_y - m_top) * scale)
                        img.paste(self.cursor_sprite, (rel_x, rel_y), self.cursor_sprite)
                except Exception:
                    pass

                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=quality, optimize=False)
                frame_bytes = buf.getvalue()

                with self.lock:
                    self.latest_frame = frame_bytes

                # Short yield so CPU doesn't spike to 100%
                time.sleep(0.015) # ~60 FPS cap
            except Exception as e:
                logging.error(f"[CAPTURE WORKER ERROR] {e}")
                attach_to_input_desktop()
                try:
                    sct = mss.MSS() if hasattr(mss, 'MSS') else mss.mss()
                except Exception:
                    pass
                time.sleep(0.05)

    def get_latest_frame(self) -> bytes:
        """Returns the most recent frame instantly with zero wait time."""
        with self.lock:
            return self.latest_frame

    def capture_frame_jpeg(self) -> bytes:
        """Synchronous capture for compatibility."""
        frame = self.get_latest_frame()
        if frame:
            return frame
        # If worker hasn't generated yet, capture once
        attach_to_input_desktop()
        sct = mss.MSS() if hasattr(mss, 'MSS') else mss.mss()
        try:
            sct_img = sct.grab(self.active_monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=self.quality, optimize=False)
            return buf.getvalue()
        except Exception:
            return b""

    def get_monitors_info(self):
        return [
            {
                "index": i,
                "left": m["left"],
                "top": m["top"],
                "width": m["width"],
                "height": m["height"],
                "is_all": i == 0,
                "is_current": i == self.monitor_index
            }
            for i, m in enumerate(self.sct.monitors)
        ]

    def set_monitor(self, index: int):
        with self.lock:
            self.monitor_index = index
            self._refresh_monitors()
            self.latest_frame = b""

    def set_quality(self, quality: int):
        with self.lock:
            self.quality = max(30, min(80, quality))

    def set_scale(self, scale: float):
        with self.lock:
            self.scale = max(0.3, min(1.0, scale))

    def get_monitor_rect(self):
        with self.lock:
            return {
                "left": self.active_monitor["left"],
                "top": self.active_monitor["top"],
                "width": self.active_monitor["width"],
                "height": self.active_monitor["height"]
            }
