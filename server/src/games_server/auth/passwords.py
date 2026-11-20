"""Hashing and checking the site password.

The server is configured with a hash of the password, never the password
itself. If the environment leaks (a log, a hosting dashboard, a crash report),
the hash alone doesn't let anyone in, and a password used elsewhere stays safe.

Argon2id is built to be slow and memory-hungry, which makes guessing the
password from a leaked hash expensive. A hash string records its own salt and
cost settings, e.g. `$argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>`, so a hash
made with different settings still verifies.
"""

from argon2 import PasswordHasher, extract_parameters
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Return a new salted Argon2id hash. Hashing twice gives different strings."""
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerificationError:  # Raised for a wrong password, not returned as False.
        return False


def is_password_hash(value: str) -> bool:
    """Whether `value` is a well-formed Argon2 hash string."""
    try:
        extract_parameters(value)
    except InvalidHashError:
        return False
    return True
