import logging
import re

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import get_settings
from app.dependencies import get_current_user_optional
from app.security import hash_password, verify_password
from app.templating import templates
from app.users import User, UserStore, get_user_store

logger = logging.getLogger(__name__)
settings = get_settings()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Messages shown on the login page after a failed Google login
GOOGLE_ERRORS = {
    "google_failed": "Google sign-in failed. Please try again.",
    "email_unverified": "Your Google email is not verified.",
    "email_exists": "An account with this email already exists. Please sign in with your password.",
}

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

router = APIRouter(tags=["auth"])


def _render(request: Request, name: str, status_code: int = 200, **context):
    return templates.TemplateResponse(request, name, context, status_code=status_code)


def _start_session(request: Request, user: User) -> RedirectResponse:
    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


# ---------- Email + password ----------

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    error = GOOGLE_ERRORS.get(request.query_params.get("error", ""))
    return _render(request, "login.html", error=error)


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    store: UserStore = Depends(get_user_store),
):
    email = email.strip().lower()
    user = await store.get_by_email(email)

    error = "Invalid email or password."
    if user and not user.password_hash:
        error = "This account uses Google sign-in. Please click “Continue with Google”."
    elif user and await verify_password(user.password_hash, password):
        logger.info("Password login: %s", user.email)
        return _start_session(request, user)

    return _render(request, "login.html", 401, error=error, email=email)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return _render(request, "register.html")


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    store: UserStore = Depends(get_user_store),
):
    name = name.strip()
    email = email.strip().lower()

    error: str | None = None
    if not 2 <= len(name) <= 60:
        error = "Name must be between 2 and 60 characters."
    elif not EMAIL_RE.match(email):
        error = "Please enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif len(password) > 128:
        error = "Password is too long (max 128 characters)."
    elif password != confirm_password:
        error = "Passwords do not match."
    elif await store.get_by_email(email):
        error = "An account with this email already exists. Try signing in."

    if error:
        return _render(request, "register.html", 400, error=error, name=name, email=email)

    user = await store.create(
        User(name=name, email=email, password_hash=await hash_password(password))
    )
    logger.info("Registered new user: %s", user.email)
    return _start_session(request, user)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ---------- Google OAuth ----------

@router.get("/auth/google")
async def google_login(request: Request):
    """Send the user to Google."""
    return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)


@router.get("/auth/callback")
async def google_callback(request: Request, store: UserStore = Depends(get_user_store)):
    """Google sends the user back here."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as exc:
        logger.warning("OAuth error: %s", exc.error)
        return RedirectResponse("/login?error=google_failed", status_code=303)

    info = token.get("userinfo") or await oauth.google.userinfo(token=token)
    email = (info.get("email") or "").lower()
    if not email or not info.get("email_verified", False):
        return RedirectResponse("/login?error=email_unverified", status_code=303)

    user = await store.get_by_google_id(info["sub"])
    if user is None:
        # First Google login: auto-register, unless the email is already taken
        if await store.get_by_email(email):
            return RedirectResponse("/login?error=email_exists", status_code=303)
        user = await store.create(
            User(
                name=info.get("name") or email,
                email=email,
                picture=info.get("picture"),
                google_id=info["sub"],
            )
        )
        logger.info("Registered new Google user: %s", user.email)
    else:
        # Returning user: refresh name and avatar
        user.name = info.get("name") or user.name
        user.picture = info.get("picture") or user.picture
        await store.update(user)
        logger.info("Google login: %s", user.email)

    return _start_session(request, user)