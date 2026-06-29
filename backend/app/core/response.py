from typing import Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any = None


class PageData(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


def ok(data: Any = None) -> dict:
    return ApiResponse(data=data).model_dump()


def fail(code: int, message: str) -> dict:
    return ApiResponse(code=code, message=message, data=None).model_dump()


def paginated(items: list, total: int, page: int, page_size: int) -> dict:
    return ok(PageData(items=items, total=total, page=page, page_size=page_size).model_dump())
