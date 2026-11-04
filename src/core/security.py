"""
Authentication & JWT Token Management
Handles cryptographic token issuance and verification for FinSolve enterprise personas.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import jwt
from pydantic import BaseModel

# Secret key for signing tokens (In production, load via AWS Secrets Manager)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "finsolve-enterprise-rag-super-secret-key-2024")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class TokenData(BaseModel):
    username: str
    roles: List[str]
    department: str


# Pre-configured Enterprise Test Personas for FinSolve Technologies
TEST_PERSONAS = {
    "alice_finance": {
        "username": "alice.finance",
        "roles": ["Finance", "Employee"],
        "department": "finance"
    },
    "bob_hr": {
        "username": "bob.hr",
        "roles": ["HR", "Employee"],
        "department": "hr"
    },
    "charlie_employee": {
        "username": "charlie.general",
        "roles": ["Employee"],
        "department": "general"
    },
    "dana_clevel": {
        "username": "dana.ceo",
        "roles": ["C-Level"],
        "department": "executive"
    },
    "evan_engineering": {
        "username": "evan.tech",
        "roles": ["Engineering", "Employee"],
        "department": "engineering"
    }
}


def create_access_token(username: str, roles: List[str], department: str, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a cryptographically signed JWT bearer token containing user roles."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": username,
        "roles": roles,
        "department": department,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> TokenData:
    """Verifies and decodes the JWT token. Raises ValueError if invalid or expired."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return TokenData(
            username=payload["sub"],
            roles=payload["roles"],
            department=payload["department"]
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired. Please re-authenticate.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid authentication token.")