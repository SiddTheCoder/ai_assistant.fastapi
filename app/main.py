# app/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import chat,tts,stt,auth
from app.socket.socket_server import sio,connected_users,socket_app
from app.socket.socket_utils import init_socket_utils
from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.db.indexes import create_indexes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Lifespan context manager (Modern way for startup/shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ========== STARTUP ==========
    logging.info("🚀 Application starting up...")
    
    await connect_to_mongo()
    await create_indexes()
    logging.info("✅ Database connected")
    
    logging.info("📡 WebSocket server available at /ws")
    init_socket_utils(sio, connected_users)
    logging.info("✅ Application startup complete")
    
    yield  # Application is running
    
    # ========== SHUTDOWN ==========
    logging.info("👋 Application shutting down...")
    
    await close_mongo_connection()
    logging.info("✅ Database disconnected")

    # Cleanup resources
    from app.utils.async_utils import cleanup_executor
    cleanup_executor()
    logging.info("✅ Application shutdown complete")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Your AI Assistant API",
    description="FastAPI backend with WebSocket support",
    version="1.0.0",
    lifespan=lifespan  # ← Modern way!
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: ["https://yourfrontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "message": "Your AI assistant is ready !!!",
        "socket": "/socket.io",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Include routes
app.include_router(chat.router)
app.include_router(tts.router)
app.include_router(stt.router)
app.include_router(auth.router)


# Mount WebSocket
app.mount("/socket.io", socket_app)