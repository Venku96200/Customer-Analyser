from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import models  # Registers SQLAlchemy models before create_all().
from database import Base, engine
from routers import auth, predictions

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Customer.Ai", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(predictions.router)


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(BASE_DIR / "templates" / "login.html")


@app.get("/app", include_in_schema=False)
def prediction_page():
    return FileResponse(BASE_DIR / "index.html")
