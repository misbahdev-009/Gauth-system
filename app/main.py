import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth import router as auth_router
from app.config import get_settings
from app.dependencies import get_current_user, get_current_user_optional
from app.templating import templates
from app.users import User, get_user_store

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

BASE_DIR = Path(__file__).resolve().parent
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_user_store().init()  # creates DB indexes when using MongoDB
    yield


app = FastAPI(title="My App", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    session_cookie="session",
    max_age=60 * 60 * 24 * 7,  # 7 days
    same_site="lax",
    https_only=settings.https_only,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(auth_router)


@app.get("/")
async def home(user: User | None = Depends(get_current_user_optional)):
    return RedirectResponse("/dashboard" if user else "/login", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "dashboard.html", {"user": user})


@app.get("/health")
async def health():
    return {"status": "ok"}