import logging
from fastapi import FastAPI
from app.routes import chat

# Configure root logger before creating app
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Ensure module loggers propagate to root
logging.getLogger("app").propagate = True

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Your AI assistant is ready !!!"}

app.include_router(chat.router)
