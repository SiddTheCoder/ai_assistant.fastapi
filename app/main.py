# app/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import chat
from app.socket.socket_server import socket_app

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
    
    # TODO: Connect to database
    # await connect_to_mongo()
    # logging.info("✅ Database connected")
    
    logging.info("📡 WebSocket server available at /ws")
    logging.info("✅ Application startup complete")
    
    yield  # Application is running
    
    # ========== SHUTDOWN ==========
    logging.info("👋 Application shutting down...")
    
    #TODO : Close database connection
    # await close_mongo_connection()
    # logging.info("✅ Database disconnected")
    
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

# Mount WebSocket
app.mount("/socket.io", socket_app)