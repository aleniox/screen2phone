"""
High-Performance WebSocket Screen Streaming and Touch Input Server.
Serves JPEG frames over binary WebSocket packets and handles touch/mouse events.
"""

import asyncio
import json
import logging
import time
import websockets
from screen_capture import ScreenCapture
from input_handler import InputHandler

class StreamServer:
    def __init__(self, host="0.0.0.0", port=8080, monitor_index=2, target_fps=60):
        self.host = host
        self.port = port
        self.target_fps = target_fps
        self.capture = ScreenCapture(monitor_index=monitor_index)
        self.input_handler = InputHandler(self.capture.get_monitor_rect())
        self.active_connections = set()
        self.running = False

    async def _send_frames_loop(self, websocket):
        """Streams captured screen frames as binary JPEG packets with zero queue lag."""
        frames_sent = 0
        stat_timer = time.time()

        while self.running and websocket in self.active_connections:
            interval = 1.0 / self.target_fps
            t0 = time.time()
            try:
                # Anti-Buffer Bloat: Drop frame if socket write buffer has backed up
                if hasattr(websocket, 'transport') and websocket.transport:
                    buf_size = websocket.transport.get_write_buffer_size()
                    if buf_size > 80 * 1024:
                        await asyncio.sleep(0.005)
                        continue

                frame_bytes = self.capture.get_latest_frame()
                if not frame_bytes:
                    await asyncio.sleep(0.005)
                    continue

                # Send the newest available frame directly
                await websocket.send(frame_bytes)
                frames_sent += 1

                # Log stats
                if time.time() - stat_timer >= 5.0:
                    fps = frames_sent / (time.time() - stat_timer)
                    logging.info(f"[STREAM] Active streaming to client: ~{fps:.1f} FPS, size: {len(frame_bytes)/1024:.1f} KB/frame")
                    frames_sent = 0
                    stat_timer = time.time()

                # Dynamic throttle to match target_fps
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
                        if "monitor_index" in data:
                            self.capture.set_monitor(int(data["monitor_index"]))
                            self.input_handler.update_monitor_rect(self.capture.get_monitor_rect())
                        logging.info(f"[CONFIG] Updated: FPS={self.target_fps}, Q={self.capture.quality}, Scale={self.capture.scale}, Monitor={self.capture.monitor_index}")
                    
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

    async def _handler(self, websocket):
        logging.info(f"Client connected: {websocket.remote_address}")
        self.active_connections.add(websocket)

        # Send initial device/screen info
        init_data = {
            "type": "init",
            "monitors": self.capture.get_monitors_info(),
            "active_monitor": self.capture.monitor_index,
            "rect": self.capture.get_monitor_rect(),
            "fps": self.target_fps,
            "quality": self.capture.quality,
            "scale": self.capture.scale
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

        self.active_connections.discard(websocket)
        logging.info(f"Client disconnected: {websocket.remote_address}")

    async def start(self):
        self.running = True
        self.capture.start_worker()
        logging.info(f"Starting Screen Stream Server on ws://{self.host}:{self.port}")
        logging.info(f"Streaming target: Monitor {self.capture.monitor_index} ({self.capture.get_monitor_rect()['width']}x{self.capture.get_monitor_rect()['height']})")
        
        async with websockets.serve(
            self._handler,
            self.host,
            self.port,
            max_size=10 * 1024 * 1024, # 10 MB max frame size
            ping_interval=25,
            ping_timeout=25
        ):
            await asyncio.Future() # run forever

    def stop(self):
        self.running = False
        self.capture.stop_worker()
