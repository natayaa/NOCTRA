from dataclasses import dataclass
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


@dataclass(slots=True)
class PageParams:
    page: int
    size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


def page_params(
    page: int = Query(1, ge=1, le=10_000),
    size: int = Query(25, ge=1, le=200),
) -> PageParams:
    return PageParams(page=page, size=size)


class PageMeta(BaseModel):
    page: int
    size: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool


class Page(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    meta: PageMeta


async def paginate(
    db: AsyncSession,
    stmt: Select,
    params: PageParams,
) -> tuple[list, PageMeta]:
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(total_stmt)).scalar_one()
    rows = (await db.execute(stmt.offset(params.offset).limit(params.limit))).scalars().all()
    pages = max(1, (total + params.size - 1) // params.size)
    meta = PageMeta(
        page=params.page,
        size=params.size,
        total=total,
        pages=pages,
        has_next=params.page < pages,
        has_prev=params.page > 1,
    )
    return list(rows), meta