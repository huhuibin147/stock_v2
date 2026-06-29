from fastapi import APIRouter

from app.core.response import ok

router = APIRouter()


@router.get("/health")
async def health():
    return ok({"status": "ok"})
