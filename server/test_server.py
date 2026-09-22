import unittest
from input_handler import InputHandler
from screen_capture import ScreenCapture
from vdd_manager import VDDManager

class TestServerComponents(unittest.TestCase):
    def test_input_coords_mapping(self):
        handler = InputHandler({"left": 1920, "top": 0, "width": 1920, "height": 1080})
        # Test center coordinate
        rx, ry = handler._to_screen_coords(0.5, 0.5)
        self.assertEqual(rx, 1920 + 960)
        self.assertEqual(ry, 540)

        # Test boundary clamping
        rx, ry = handler._to_screen_coords(-0.2, 1.5)
        self.assertEqual(rx, 1920)
        self.assertEqual(ry, 1080)

    def test_screen_capture_frame(self):
        sct = ScreenCapture(monitor_index=1)
        monitors = sct.get_monitors_info()
        self.assertGreaterEqual(len(monitors), 1)
        
        # Test frame capture
        frame = sct.capture_frame_jpeg()
        self.assertIsInstance(frame, bytes)
        self.assertGreater(len(frame), 100) # Valid JPEG size
        # Check JPEG magic bytes: 0xFF 0xD8
        self.assertEqual(frame[0], 0xFF)
        self.assertEqual(frame[1], 0xD8)

    def test_display_count(self):
        count = VDDManager.get_display_count()
        self.assertGreaterEqual(count, 1)

if __name__ == "__main__":
    unittest.main()
