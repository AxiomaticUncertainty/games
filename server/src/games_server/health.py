"""Liveness endpoint for hosting platforms and uptime checks.

It deliberately reports nothing about the app's internals, because it will stay
reachable without a password once the site is gated.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
