from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from database import init_db
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.teams import router as teams_router
from routes.event_types import router as event_types_router
from routes.events import router as events_router
from routes.notifications import router as notifications_router
from routes.support import router as support_router
from admin.routes import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Nurser API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "null",                      # file:// opened directly in browser
        "http://localhost:3000",
        "http://localhost:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:5501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "change-me"))

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(users_router, prefix="/users", tags=["Users"])
app.include_router(teams_router, prefix="/teams", tags=["Teams"])
app.include_router(event_types_router, tags=["Event Types"])
app.include_router(events_router, prefix="/events", tags=["Events"])
app.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
app.include_router(support_router, prefix="/support", tags=["Support"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])

# Serve frontend HTML files at the root — no CORS issues
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


@app.get("/health")
def health_check():
    return {"status": "ok"}
