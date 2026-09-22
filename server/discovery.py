"""
UDP Broadcast Discovery Service for Wi-Fi connections.
Allows mobile devices on the same Wi-Fi network to discover this PC server automatically.
"""

import socket
import json
import threading
import time
import logging

DISCOVERY_PORT = 8088
MAGIC_REQUEST = "DISCOVER_SECOND_SCREEN"

def get_local_ip_addresses():
    """Returns all non-loopback IPv4 addresses of the local machine."""
    ip_list = []
    try:
        # Connect to a dummy external address to find primary route
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
        if primary_ip and not primary_ip.startswith("127."):
            ip_list.append(primary_ip)
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and not ip.startswith("169.254.") and ip not in ip_list:
                ip_list.append(ip)
    except Exception:
        pass

    return ip_list

class DiscoveryServer:
    def __init__(self, ws_port=8080):
        self.ws_port = ws_port
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def _run_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(1.0)

        try:
            sock.bind(("", DISCOVERY_PORT))
            logging.info(f"[WIFI DISCOVERY] UDP discovery listening on port {DISCOVERY_PORT}")
        except Exception as e:
            logging.warning(f"[WIFI DISCOVERY] Could not bind UDP discovery port: {e}")
            return

        hostname = socket.gethostname()
        local_ips = get_local_ip_addresses()
        primary_ip = local_ips[0] if local_ips else "127.0.0.1"

        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode('utf-8', errors='ignore').strip()
                
                if MAGIC_REQUEST in message:
                    response_data = {
                        "service": "second_screen_server",
                        "hostname": hostname,
                        "ip": primary_ip,
                        "port": self.ws_port,
                        "ws_url": f"ws://{primary_ip}:{self.ws_port}"
                    }
                    reply = json.dumps(response_data).encode('utf-8')
                    sock.sendto(reply, addr)
                    logging.info(f"[WIFI DISCOVERY] Responded to discovery from {addr[0]}")
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logging.debug(f"[WIFI DISCOVERY] Error in discovery loop: {e}")
                break

        sock.close()
