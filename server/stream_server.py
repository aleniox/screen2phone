"""
High-Performance WebSocket Screen Streaming and Touch Input Server.
Serves JPEG frames over binary WebSocket packets and handles touch/mouse events.
"""

import asyncio
import json
import logging
import socket
import time
import websockets
from screen_capture import ScreenCapture
from input_handler import InputHandler

def is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """Check if a TCP port is available to bind on host."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False

def find_available_port(preferred_port: int = 8080, fallback_ports=(8082, 8085, 8888, 7070, 7777, 9000)) -> int:
    """Finds an available TCP port starting with preferred_port, then checking fallback_ports."""
    if is_port_available(preferred_port):
        return preferred_port
    for port in fallback_ports:
        if is_port_available(port):
            return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class StreamServer:
    def __init__(self, host="0.0.0.0", port=8080, monitor_index=2, target_fps=60):
        self.host = host
        self.port = port
        self.target_fps = target_fps
        self.max_bitrate = 3.5 * 1024 * 1024  # 3.5 MB/s (~28 Mbps) bandwidth ceiling to prevent ADB buffer spikes
        self.capture = ScreenCapture(monitor_index=monitor_index)
        self.input_handler = InputHandler(self.capture.get_monitor_rect())
        self.active_connections = set()
        self.running = False

    async def _send_frames_loop(self, websocket):
        """Streams captured screen frames with dynamic bitrate ceiling and zero queue lag."""
        frames_sent = 0
        total_bytes_sent = 0
        stat_timer = time.time()
        last_sent_frame = None
        last_send_time = 0.0
        MAX_IDLE_INTERVAL = 0.15  # Max interval between identical frames (~6.6 FPS idle heartbeat)

        while self.running and websocket in self.active_connections:
            t0 = time.time()
            try:
                # Anti-Buffer Bloat: Drop frame if socket write buffer has backed up
                if hasattr(websocket, 'transport') and websocket.transport:
                    buf_size = websocket.transport.get_write_buffer_size()
                    if buf_size > 32 * 1024:
                        await asyncio.sleep(0.002)
                        continue

                frame_bytes = self.capture.get_latest_frame()
                if not frame_bytes:
                    await asyncio.sleep(0.002)
                    continue

                # Idle Screen Deduplication:
                # If frame is identical to last sent frame, throttle to ~6.6 FPS heartbeat
                # This saves 85-90% bandwidth when the user is reading or idle
                is_duplicate = (frame_bytes == last_sent_frame)
                if is_duplicate and (t0 - last_send_time < MAX_IDLE_INTERVAL):
                    await asyncio.sleep(0.005)
                    continue

                # Send the newest available frame directly
                await websocket.send(frame_bytes)
                last_sent_frame = frame_bytes
                last_send_time = t0
                frame_size = len(frame_bytes)
                frames_sent += 1
                total_bytes_sent += frame_size

                # Dynamic Bitrate Limiter:
                # Calculates minimum interval based on frame size and max_bitrate.
                # Guarantees bandwidth strictly never exceeds self.max_bitrate (e.g. 3.5 MB/s ~ 28 Mbps)
                # under heavy window dragging or full-screen pixel updates.
                target_interval = 1.0 / self.target_fps
                bitrate_min_interval = frame_size / self.max_bitrate if self.max_bitrate > 0 else 0
                interval = max(target_interval, bitrate_min_interval)

                # Log stats every 5 seconds
                now = time.time()
                if now - stat_timer >= 5.0:
                    dt = now - stat_timer
                    fps = frames_sent / dt
                    mbps = (total_bytes_sent * 8) / (dt * 1024 * 1024)
                    avg_size_kb = (total_bytes_sent / frames_sent) / 1024 if frames_sent > 0 else 0
                    logging.info(f"[STREAM] ~{fps:.1f} FPS | avg {avg_size_kb:.1f} KB/frame | ~{mbps:.2f} Mbps")
                    frames_sent = 0
                    total_bytes_sent = 0
                    stat_timer = now

                # Throttle to matching interval
                elapsed = time.time() - t0
                if elapsed < interval:
                    await asyncio.sleep(interval - elapsed)

            except websockets.exceptions.ConnectionClosed:
                break
            except Exception as e:
                logging.warning(f"Error sending frame: {e}")
                break

    async def _receive_input_loop(self, websocket):
        """Receives control messages and touch/pointer events from the client."""
        try:
            async for message in websocket:
                try:
                    if isinstance(message, str):
                        data = json.loads(message)
                        msg_type = data.get("type")

                        if msg_type == "config":
                            if "fps" in data:
                                self.target_fps = max(10, min(120, int(data["fps"])))
                            if "quality" in data:
                                self.capture.set_quality(int(data["quality"]))
                            if "scale" in data:
                                self.capture.set_scale(float(data["scale"]))
                            if "speed" in data:
                                self.input_handler.set_speed(float(data["speed"]))
                            if "bitrate_mbps" in data:
                                self.max_bitrate = max(1.0, min(30.0, float(data["bitrate_mbps"]))) * 1024 * 1024 / 8
                            if "monitor_index" in data:
                                self.capture.set_monitor(int(data["monitor_index"]))
                                self.input_handler.update_monitor_rect(self.capture.get_monitor_rect())
                            logging.info(f"[CONFIG] Updated: FPS={self.target_fps}, Q={self.capture.quality}, Scale={self.capture.scale}, Speed={self.input_handler.mouse_speed}, MaxBitrate={self.max_bitrate*8/(1024*1024):.1f}Mbps, Monitor={self.capture.monitor_index}")
                            await self.broadcast_info()
                        
                        elif msg_type == "get_monitors":
                            resp = {
                                "type": "monitors_list",
                                "monitors": self.capture.get_monitors_info(),
                                "current": self.capture.monitor_index
                            }
                            await websocket.send(json.dumps(resp))

                        else:
                            # Forward touch/mouse event to input handler
                            self.input_handler.handle_event(data)

                except Exception as e:
                    logging.warning(f"Error handling incoming message: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass # Client disconnected normally or socket closed
        except Exception as e:
            logging.debug(f"Input loop finished: {e}")

    async def broadcast_info(self):
        """Broadcasts updated screen and config info to all connected clients."""
        info_packet = {
            "type": "init",
            "monitors": self.capture.get_monitors_info(),
            "active_monitor": self.capture.monitor_index,
            "rect": self.capture.get_monitor_rect(),
            "fps": self.target_fps,
            "quality": self.capture.quality,
            "scale": self.capture.scale,
            "bitrate_mbps": round((self.max_bitrate * 8) / (1024 * 1024), 1)
        }
        msg = json.dumps(info_packet)
        for ws in list(self.active_connections):
            try:
                await ws.send(msg)
            except Exception:
                pass

    async def _handler(self, websocket):
        logging.info(f"Client connected: {websocket.remote_address}")
        self.active_connections.add(websocket)

        # Start / resume capture worker when client connects
        if not self.capture.running:
            self.capture.start_worker()

        # Send initial device/screen info
        init_data = {
            "type": "init",
            "monitors": self.capture.get_monitors_info(),
            "active_monitor": self.capture.monitor_index,
            "rect": self.capture.get_monitor_rect(),
            "fps": self.target_fps,
            "quality": self.capture.quality,
            "scale": self.capture.scale,
            "bitrate_mbps": round((self.max_bitrate * 8) / (1024 * 1024), 1)
        }
        await websocket.send(json.dumps(init_data))

        send_task = asyncio.create_task(self._send_frames_loop(websocket))
        recv_task = asyncio.create_task(self._receive_input_loop(websocket))

        done, pending = await asyncio.wait(
            [send_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, websockets.exceptions.ConnectionClosed, Exception):
                pass

        for task in done:
            try:
                task.result()
            except (websockets.exceptions.ConnectionClosed, Exception):
                pass

        self.active_connections.discard(websocket)
        logging.info(f"Client disconnected: {websocket.remote_address}")

        # Reset mouse state (release any held buttons)
        self.input_handler.reset()

        # Pause capture worker if no clients are connected to save CPU/battery
        if len(self.active_connections) == 0:
            logging.info("No active clients. Pausing screen capture worker.")
            self.capture.stop_worker()

    async def start(self):
        self.running = True
        logging.info(f"Starting Screen Stream Server on ws://{self.host}:{self.port}")
        logging.info(f"Streaming target: Monitor {self.capture.monitor_index} ({self.capture.get_monitor_rect()['width']}x{self.capture.get_monitor_rect()['height']})")
        
        async with websockets.serve(
            self._handler,
            self.host,
            self.port,
            max_size=10 * 1024 * 1024, # 10 MB max frame size
            write_limit=256 * 1024,    # 256 KB write limit to avoid choking on large dynamic frames
            ping_interval=20,
            ping_timeout=20
        ):
            await asyncio.Future() # run forever

    def stop(self):
        self.running = False
        self.capture.stop_worker()
        self.input_handler.reset()
