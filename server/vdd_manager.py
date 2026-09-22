"""
Virtual Display Driver (VDD) Manager for Windows.
Allows detecting monitors, and provides utilities to install or enable
a virtual secondary display (IddCx / usbmmidd) on Windows 10/11.
"""

import os
import sys
import ctypes
import urllib.request
import zipfile
import subprocess
import logging

class VDDManager:
    """Manages Virtual Display Driver on Windows."""
    
    USBMMIDD_URL = "https://www.amyuni.com/downloads/usbmmidd_v2.zip"
    VDD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vdd_driver")

    @staticmethod
    def get_display_count() -> int:
        """Returns the number of monitors currently recognized by Windows."""
        return ctypes.windll.user32.GetSystemMetrics(80) # SM_CMONITORS

    @classmethod
    def download_and_extract_driver(cls):
        """Downloads usbmmidd virtual display driver if not already present."""
        os.makedirs(cls.VDD_DIR, exist_ok=True)
        zip_path = os.path.join(cls.VDD_DIR, "usbmmidd_v2.zip")
        installer = os.path.join(cls.VDD_DIR, "usbmmidd_v2", "deviceinstaller64.exe")

        if os.path.exists(installer):
            logging.info("Virtual display driver files already present.")
            return True, installer

        logging.info("Downloading Virtual Display Driver (usbmmidd)...")
        try:
            req = urllib.request.Request(
                cls.USBMMIDD_URL,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=30) as response, open(zip_path, 'wb') as out_file:
                out_file.write(response.read())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(cls.VDD_DIR)
                
            logging.info("Driver downloaded and extracted successfully.")
            return True, installer
        except Exception as e:
            logging.error(f"Failed to download driver: {e}")
            return False, str(e)

    @classmethod
    def enable_virtual_monitor(cls):
        """Enables a virtual monitor using the device installer."""
        success, installer = cls.download_and_extract_driver()
        if not success:
            return False, f"Could not obtain driver: {installer}"
        
        driver_dir = os.path.dirname(installer)
        cmd_install = f'"{installer}" install usbmmidd.inf usbmmidd'
        cmd_enable = f'"{installer}" enableidd 1'
        
        try:
            logging.info("Installing driver service...")
            subprocess.run(cmd_install, shell=True, cwd=driver_dir, capture_output=True, text=True)
            logging.info("Activating virtual monitor...")
            res = subprocess.run(cmd_enable, shell=True, cwd=driver_dir, capture_output=True, text=True)
            return True, res.stdout
        except Exception as e:
            return False, str(e)

    @classmethod
    def disable_virtual_monitor(cls):
        """Deactivates the virtual monitor."""
        installer = os.path.join(cls.VDD_DIR, "usbmmidd_v2", "deviceinstaller64.exe")
        if not os.path.exists(installer):
            return False, "Driver not installed"
        driver_dir = os.path.dirname(installer)
        cmd_disable = f'"{installer}" enableidd 0'
        try:
            res = subprocess.run(cmd_disable, shell=True, cwd=driver_dir, capture_output=True, text=True)
            return True, res.stdout
        except Exception as e:
            return False, str(e)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    count = VDDManager.get_display_count()
    print(f"Current Windows Monitor Count: {count}")
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        if action == "enable":
            ok, msg = VDDManager.enable_virtual_monitor()
            print(f"Enable result: {ok}, {msg}")
        elif action == "disable":
            ok, msg = VDDManager.disable_virtual_monitor()
            print(f"Disable result: {ok}, {msg}")
