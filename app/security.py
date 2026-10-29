from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from starlette.concurrency import run_in_threadpool

_hasher = PasswordHasher()


async def hash_password(password: str) -> str:
    """Turn a password into a safe hash. Hashing is slow on purpose, so run it in a thread."""
    return await run_in_threadpool(_hasher.hash, password)


async def verify_password(password_hash: str, password: str) -> bool:
    def _check() -> bool:
        try:
            return _hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False

    return await run_in_threadpool(_check)