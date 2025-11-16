from typing import List
from fastapi import WebSocket
import asyncio

class WebSocketManager:
  def __init__(self):
    # list of connected websockets
    self.active_websockets: List[WebSocket] = []
    # prevent race conditions
    self.lock = asyncio.Lock()
    
  async def connect(self, websocket: WebSocket):
    await websocket.accept()
    self.active_websockets.append(websocket)

  def disconnect(self, websocket: WebSocket):
    self.active_websockets.remove(websocket)

  async def send_to_one(self, websocket: WebSocket, message: dict):
    """
    Sends JSON to a specific client.
    """
    await websocket.send_json(message)

  async def broadcast(self, message: dict):
    async with self.lock:
        connections = list(self.active_websockets)
    for ws in connections:
        try:
            await ws.send_json(message)
        except:
            # if failed, ignore - disconnect logic will handle cleaning
            pass  