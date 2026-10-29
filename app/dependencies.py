from fastapi import Depends, HTTPException, Request

from app.users import User, UserStore, get_user_store


async def get_current_user_optional(
    request: Request, store: UserStore = Depends(get_user_store)
) -> User | None:
    """Returns the logged-in user, or None."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = await store.get_by_id(user_id)
    if user is None:  # stale cookie (e.g. server restarted)
        request.session.clear()
    return user


async def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    """Use on protected routes. Redirects to /login if not logged in."""
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user