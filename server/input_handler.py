"""
Input Handler for Windows: Translates touch gestures and pointer events
from the mobile client into native Windows mouse and touch input.
"""

import ctypes
import logging
import win32api

# Win32 Mouse Event Flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

user32 = ctypes.windll.user32

class InputHandler:
    def __init__(self, monitor_rect=None):
        """
        monitor_rect: dict with 'left', 'top', 'width', 'height'
        """
        self.monitor_rect = monitor_rect or {"left": 0, "top": 0, "width": 1920, "height": 1080}
        self.is_mouse_down = False
        self.mouse_speed = 1.5
        logging.info(f"InputHandler initialized for monitor: {self.monitor_rect}")

    def update_monitor_rect(self, rect):
        self.monitor_rect = rect
        logging.info(f"InputHandler monitor updated: {self.monitor_rect}")

    def set_speed(self, speed: float):
        self.mouse_speed = max(0.5, min(5.0, float(speed)))

    def reset(self):
        """Release any held mouse buttons and reset state."""
        try:
            if self.is_mouse_down:
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                self.is_mouse_down = False
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        except Exception:
            pass

    def _to_screen_coords(self, norm_x: float, norm_y: float):
        """Convert normalized (0.0 - 1.0) coordinates to absolute Windows pixel coordinates."""
        clamped_x = max(0.0, min(1.0, norm_x))
        clamped_y = max(0.0, min(1.0, norm_y))
        
        real_x = self.monitor_rect["left"] + int(clamped_x * self.monitor_rect["width"])
        real_y = self.monitor_rect["top"] + int(clamped_y * self.monitor_rect["height"])
        return real_x, real_y

    def handle_event(self, data: dict):
        """
        Processes an incoming input payload from the client.
        Supported event types:
          - mouse_move:   { type: 'mouse_move', dx: float, dy: float, speed: float }
          - pointer_down: { type: 'pointer_down', x: float, y: float, button: 'left'|'right' }
          - pointer_move: { type: 'pointer_move', x: float, y: float }
          - pointer_up:   { type: 'pointer_up', x: float, y: float, button: 'left'|'right' }
          - tap:          { type: 'tap', x: float, y: float }
          - right_tap:    { type: 'right_tap', x: float, y: float }
          - double_tap:   { type: 'double_tap', x: float, y: float }
          - scroll:       { type: 'scroll', dy: int }
        """
        event_type = data.get("type")
        if not event_type:
            return

        # Relative mouse movement (Trackpad mode)
        if event_type == "mouse_move":
            dx = data.get("dx", 0.0)
            dy = data.get("dy", 0.0)
            speed = data.get("speed", self.mouse_speed)
            move_x = int(dx * speed)
            move_y = int(dy * speed)
            if move_x != 0 or move_y != 0:
                user32.mouse_event(MOUSEEVENTF_MOVE, move_x, move_y, 0, 0)
            return

        x = data.get("x")
        y = data.get("y")

        if x is not None and y is not None:
            real_x, real_y = self._to_screen_coords(x, y)
            user32.SetCursorPos(real_x, real_y)
        else:
            real_x, real_y = 0, 0

        if event_type == "pointer_down":
            button = data.get("button", "left")
            if button == "right":
                user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            else:
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                self.is_mouse_down = True

        elif event_type == "pointer_move":
            pass # SetCursorPos already executed above

        elif event_type == "pointer_up":
            button = data.get("button", "left")
            if button == "right":
                user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            else:
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                self.is_mouse_down = False

        elif event_type == "tap":
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

        elif event_type == "right_tap":
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

        elif event_type == "double_tap":
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

        elif event_type == "scroll":
            dy = data.get("dy", 0)
            # WHEEL_DELTA is typically 120
            wheel_amount = int(dy * 120)
            user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, wheel_amount, 0)
