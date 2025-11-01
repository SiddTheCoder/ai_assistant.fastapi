from fastapi import FastAPI
from app.routes import chat

app = FastAPI()

@app.get("/")
def read_root():
  return {"message":'Your ai assistant is ready !!!'}

app.include_router(chat.router)