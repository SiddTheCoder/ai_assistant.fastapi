import socketio

# Create an AsyncServer instance
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*'
)

# Create an ASGI app
socket_app = socketio.ASGIApp(sio)

# Example event handler
@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")