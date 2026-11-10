import logging
from datetime import datetime, timezone
from functools import lru_cache
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field

from app.config import get_settings

logger = logging.getLogger(__name__)


class User(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    email: str
    picture: str | None = None
    google_id: str | None = None        # set for Google accounts
    password_hash: str | None = None    # set for email/password accounts
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def initials(self) -> str:
        parts = self.name.strip().split()
        return "".join(p[0] for p in parts[:2]).upper() or "?"

    @property
    def first_name(self) -> str:
        parts = self.name.strip().split()
        return parts[0] if parts else self.name

    @property
    def provider(self) -> str:
        return "Google" if self.google_id else "Email & password"


class UserStore(Protocol):
    async def init(self) -> None: ...
    async def get_by_id(self, user_id: str) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def get_by_google_id(self, google_id: str) -> User | None: ...
    async def create(self, user: User) -> User: ...
    async def update(self, user: User) -> None: ...


class InMemoryUserStore:
    """Data is stored in-memory (resets on server restart). Default for development."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    async def init(self) -> None:
        return None

    async def get_by_id(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._users.values() if u.email == email), None)

    async def get_by_google_id(self, google_id: str) -> User | None:
        return next((u for u in self._users.values() if u.google_id == google_id), None)

    async def create(self, user: User) -> User:
        self._users[user.id] = user
        return user

    async def update(self, user: User) -> None:
        self._users[user.id] = user


class MongoUserStore:
    """Permanent storage using MongoDB with automatic in-memory fallback on failure."""

    def __init__(self, uri: str, db_name: str) -> None:
        from pymongo import AsyncMongoClient

        self._client = AsyncMongoClient(uri, serverSelectionTimeoutMS=1500)
        self._users = self._client[db_name]["users"]
        self._fallback = InMemoryUserStore()
        self._connected = False

    async def init(self) -> None:
        try:
            await self._client.admin.command("ping")
            await self._users.create_index("id", unique=True)
            await self._users.create_index("email", unique=True)
            await self._users.create_index(
                "google_id",
                unique=True,
                partialFilterExpression={"google_id": {"$type": "string"}},
            )
            self._connected = True
            logger.info("Successfully connected to MongoDB.")
        except Exception as exc:
            self._connected = False
            logger.warning(
                "MongoDB connection failed (%s). Falling back to in-memory user store for development.",
                exc,
            )

    @staticmethod
    def _to_user(doc: dict | None) -> User | None:
        return User(**doc) if doc else None

    async def get_by_id(self, user_id: str) -> User | None:
        if not self._connected:
            return await self._fallback.get_by_id(user_id)
        try:
            return self._to_user(await self._users.find_one({"id": user_id}, {"_id": 0}))
        except Exception as exc:
            logger.warning("MongoDB get_by_id error: %s. Using fallback.", exc)
            return await self._fallback.get_by_id(user_id)

    async def get_by_email(self, email: str) -> User | None:
        if not self._connected:
            return await self._fallback.get_by_email(email)
        try:
            return self._to_user(await self._users.find_one({"email": email}, {"_id": 0}))
        except Exception as exc:
            logger.warning("MongoDB get_by_email error: %s. Using fallback.", exc)
            return await self._fallback.get_by_email(email)

    async def get_by_google_id(self, google_id: str) -> User | None:
        if not self._connected:
            return await self._fallback.get_by_google_id(google_id)
        try:
            return self._to_user(
                await self._users.find_one({"google_id": google_id}, {"_id": 0})
            )
        except Exception as exc:
            logger.warning("MongoDB get_by_google_id error: %s. Using fallback.", exc)
            return await self._fallback.get_by_google_id(google_id)

    async def create(self, user: User) -> User:
        if not self._connected:
            return await self._fallback.create(user)
        try:
            await self._users.insert_one(user.model_dump())
            await self._fallback.create(user)
            return user
        except Exception as exc:
            logger.warning("MongoDB create error: %s. Using fallback.", exc)
            return await self._fallback.create(user)

    async def update(self, user: User) -> None:
        if not self._connected:
            await self._fallback.update(user)
            return
        try:
            await self._users.update_one({"id": user.id}, {"$set": user.model_dump()})
            await self._fallback.update(user)
        except Exception as exc:
            logger.warning("MongoDB update error: %s. Using fallback.", exc)
            await self._fallback.update(user)


@lru_cache
def get_user_store() -> UserStore:
    settings = get_settings()
    if settings.mongodb_uri:
        logger.info("Configured MongoDB user store with URI: %s", settings.mongodb_uri.split("@")[-1])
        return MongoUserStore(settings.mongodb_uri, settings.mongodb_db)
    logger.warning("Using in-memory user store (data resets on restart)")
    return InMemoryUserStore()
