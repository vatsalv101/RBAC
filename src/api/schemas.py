"""
API Data Contracts (Pydantic v2)
Strict request and response schemas for the FinSolve RAG API.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    persona: str = Field(
        ...,
        description="Select a test persona: alice_finance, bob_hr, charlie_employee, dana_clevel, evan_engineering"
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    roles: List[str]
    department: str


class SearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="The question or search query"
    )
    limit: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of chunks to retrieve"
    )


class ChunkResult(BaseModel):
    id: int
    score: float
    department: Optional[str] = None
    allowed_roles: Optional[List[str]] = None
    text: str


class SearchResponse(BaseModel):
    query: str
    authenticated_user: str
    effective_roles: List[str]
    total_results: int
    results: List[ChunkResult]