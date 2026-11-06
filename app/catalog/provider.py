from typing import Protocol

from pydantic import BaseModel, Field


class CatalogContext(BaseModel):
    status: str = "unavailable"
    # Deliberately uncommitted schemas until the supplied data pack is known.
    products: list[dict] = Field(default_factory=list)
    offers: list[dict] = Field(default_factory=list)
    stock: list[dict] = Field(default_factory=list)
    finance_terms: list[dict] = Field(default_factory=list)


class CatalogProvider(Protocol):
    async def context_for(self, store_id: str) -> CatalogContext: ...


class EmptyCatalogProvider:
    async def context_for(self, store_id: str) -> CatalogContext:
        return CatalogContext()


def get_catalog() -> CatalogProvider:
    return EmptyCatalogProvider()
