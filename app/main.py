# app/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import chat, tts, stt, auth, ml_test, openrouter_debug
from app.socket.socket_server import sio, connected_users, socket_app
from app.socket.socket_utils import init_socket_utils
from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.db.indexes import create_indexes

# Import ML components
from app.ml import model_loader, embedding_worker, DEVICE, MODELS_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ========== STARTUP ==========
    logger.info("=" * 60)
    logger.info("🚀 Application starting up...")
    logger.info("=" * 60)
    
    # Connect to database
    await connect_to_mongo()
    await create_indexes() # type : ignore
    logger.info("✅ Database connected")
    
    # Initialize WebSocket
    logger.info("📡 WebSocket server available at /ws")
    init_socket_utils(sio, connected_users)
    logger.info("✅ WebSocket initialized")
    
    # Load ML models
    logger.info("=" * 60)
    logger.info(f"🤖 Loading ML models on device: {DEVICE}")
    logger.info("=" * 60)
    
    # Load all models (they should already be downloaded)
    success = model_loader.load_all_models()
    
    if success:
        logger.info("✅ All ML models loaded successfully")
        
        # Warmup models to avoid cold start
        model_loader.warmup_models()
        logger.info("✅ Models warmed up - no cold start!")
    else:
        logger.warning("⚠️  Some ML models failed to load - check logs")
    
    logger.info("=" * 60)
    logger.info("✅ Application startup complete")
    logger.info("🚀 Server is ready to handle requests!")
    logger.info("=" * 60)
    
    yield  # Application is running
    
    # ========== SHUTDOWN ==========
    logger.info("=" * 60)
    logger.info("👋 Application shutting down...")
    logger.info("=" * 60)
    
    # Cleanup database
    await close_mongo_connection()
    logger.info("✅ Database disconnected")
    
    # Cleanup ML resources
    embedding_worker.shutdown()
    model_loader.unload_all_models()
    logger.info("✅ ML models unloaded")
    
    # Cleanup other resources
    from app.utils.async_utils import cleanup_executor
    cleanup_executor()
    logger.info("✅ Application shutdown complete")
    logger.info("=" * 60)


# Create FastAPI app
app = FastAPI(
    title="AI Assistant API",
    description="FastAPI backend with ML models and WebSocket support",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5123"],  # In production: ["https://yourfrontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "message": "Your AI assistant is ready!",
        "device": DEVICE,
        "socket": "/socket.io",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "device": DEVICE,
        "models_loaded": list(model_loader._models.keys())
    }

@app.get("/ml/status")
def ml_status():
    """Check ML models status"""
    return {
        "device": DEVICE,
        "models_loaded": list(model_loader._models.keys()),
        "models_available": list(MODELS_CONFIG.keys())
    }

# Include routes
app.include_router(chat.router)
app.include_router(tts.router)
app.include_router(stt.router)
app.include_router(auth.router)
app.include_router(ml_test.router)
app.include_router(openrouter_debug.router)

# Mount WebSocket
app.mount("/socket.io", socket_app)