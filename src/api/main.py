"""
FinSolve Technologies - Enterprise RBAC RAG API
FastAPI Gateway with cryptographic JWT authentication and deterministic vector pre-filtering.
"""
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.security import (
    TEST_PERSONAS,
    TokenData,
    create_access_token,
    verify_token,
)
from src.core.rbac_translator import RBACTranslator
from src.core.embedder import Embedder
from src.vector_store.engine import VectorEngine
from src.api.schemas import (
    TokenRequest,
    TokenResponse,
    SearchRequest,
    SearchResponse,
    ChunkResult,
)

# Global singleton caches with dependency getters
_embedder: Optional[Embedder] = None
_vector_engine: Optional[VectorEngine] = None
security_scheme = HTTPBearer()


def get_embedder() -> Embedder:
    """Dependency: Lazy-loads Embedder singleton."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


def get_vector_engine() -> VectorEngine:
    """Dependency: Lazy-loads VectorEngine singleton (connects to Qdrant Cloud via .env)."""
    global _vector_engine
    if _vector_engine is None:
        _vector_engine = VectorEngine()
    return _vector_engine


app = FastAPI(
    title="FinSolve Enterprise RBAC RAG Gateway",
    description="Role-Based Access Control RAG system backed by Qdrant Cloud & Bedrock metadata.",
    version="1.0.0"
)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> TokenData:
    """Security Dependency: Validates the incoming Bearer JWT and extracts user claims."""
    token = credentials.credentials
    try:
        token_data = verify_token(token)
        return token_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/", tags=["Health"])
def root(engine: VectorEngine = Depends(get_vector_engine)):
    return {
        "service": "FinSolve Enterprise RBAC RAG Gateway",
        "status": "online",
        "cloud_cluster": engine.cloud_url if engine.is_cloud else "offline",
        "docs_url": "/docs"
    }


@app.post("/api/v1/auth/token", response_model=TokenResponse, tags=["Authentication"])
def login_for_access_token(request: TokenRequest):
    """
    Log in as a FinSolve persona to obtain a signed JWT token.
    Available personas:
      - alice_finance    (Roles: Finance, Employee)
      - bob_hr           (Roles: HR, Employee)
      - charlie_employee (Roles: Employee)
      - dana_clevel      (Roles: C-Level - Full Access)
      - evan_engineering (Roles: Engineering, Employee)
    """
    persona = request.persona.lower().strip()
    if persona not in TEST_PERSONAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown persona '{persona}'. Choose from: {list(TEST_PERSONAS.keys())}"
        )

    user_info = TEST_PERSONAS[persona]
    token = create_access_token(
        username=user_info["username"],
        roles=user_info["roles"],
        department=user_info["department"]
    )

    return TokenResponse(
        access_token=token,
        username=user_info["username"],
        roles=user_info["roles"],
        department=user_info["department"]
    )


@app.post("/api/v1/search", response_model=SearchResponse, tags=["RAG Search"])
def search_documents(
    request: SearchRequest,
    current_user: TokenData = Depends(get_current_user),
    engine: VectorEngine = Depends(get_vector_engine),
    embed_service: Embedder = Depends(get_embedder)
):
    """
    Protected Search Endpoint:
    1. Extracts caller's roles from verified JWT.
    2. Translates roles into a strict cloud vector pre-filter.
    3. Searches the cloud collection (dim=384, Cosine).
    4. Guarantees 0% data leakage across departmental silos.
    """
    # 1. Expand roles (all staff inherit 'Employee')
    effective_roles = RBACTranslator.get_effective_roles(current_user.roles)

    # 2. Vectorize user query
    query_vector = embed_service.embed_query(request.query)

    # 3. Query Cloud Vector Store with RBAC pre-filter
    hits = engine.search_with_rbac(
        query_vector=query_vector,
        user_roles=effective_roles,
        limit=request.limit
    )

    results = [
        ChunkResult(
            id=hit["id"],
            score=round(hit["score"], 4),
            department=hit.get("department"),
            allowed_roles=hit.get("allowed_roles"),
            text=hit.get("text")
        )
        for hit in hits
    ]

    return SearchResponse(
        query=request.query,
        authenticated_user=current_user.username,
        effective_roles=effective_roles,
        total_results=len(results),
        results=results
    )
