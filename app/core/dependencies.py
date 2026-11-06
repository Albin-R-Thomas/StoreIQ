from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import AIProvider, get_ai_provider
from app.catalog.provider import CatalogProvider, get_catalog
from app.db.session import get_db
from app.retrieval.provider import Retriever, get_retriever

DB = Annotated[AsyncSession, Depends(get_db)]
AI = Annotated[AIProvider, Depends(get_ai_provider)]
Catalog = Annotated[CatalogProvider, Depends(get_catalog)]
Retrieval = Annotated[Retriever, Depends(get_retriever)]
