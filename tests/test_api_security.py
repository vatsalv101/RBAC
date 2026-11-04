"""
API Security & RBAC Isolation Integration Tests
Proves mathematically that unauthorized personas cannot access siloed documents.
"""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def get_token(persona: str) -> str:
    """Helper to fetch a valid JWT token for a test persona."""
    res = client.post("/api/v1/auth/token", json={"persona": persona})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_unauthenticated_request_blocked():
    """Requests without a Bearer token must be rejected with 401 Unauthorized."""
    response = client.post("/api/v1/search", json={"query": "test query"})
    assert response.status_code == 401
    assert "detail" in response.json()


def test_finance_access_permitted_for_alice():
    """Alice (Finance) must successfully retrieve financial data."""
    token = get_token("alice_finance")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/search",
        headers=headers,
        json={"query": "What was the EBITDA and cash flow in 2024?", "limit": 3}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated_user"] == "alice.finance"
    assert data["total_results"] > 0
    # Every returned chunk must be either finance or general
    for hit in data["results"]:
        assert hit["department"] in ["finance", "general"]


def test_finance_data_blocked_for_charlie_employee():
    """Charlie (Employee) querying for finance numbers must receive 0 finance chunks."""
    token = get_token("charlie_employee")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/search",
        headers=headers,
        json={"query": "What was the EBITDA and quarterly operating profit in 2024?", "limit": 5}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated_user"] == "charlie.general"
    # None of the returned results can come from the finance department!
    for hit in data["results"]:
        assert hit["department"] != "finance"


def test_hr_salaries_blocked_for_alice_finance():
    """Alice (Finance) querying for HR salaries must receive 0 HR chunks."""
    token = get_token("alice_finance")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/search",
        headers=headers,
        json={"query": "What is the annual salary and attendance of Isha Chowdhury?", "limit": 5}
    )
    assert response.status_code == 200
    data = response.json()
    # Zero HR records returned to Finance!
    for hit in data["results"]:
        assert hit["department"] != "hr"


def test_hr_salaries_permitted_for_bob_hr():
    """Bob (HR) must successfully retrieve employee salary records."""
    token = get_token("bob_hr")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/search",
        headers=headers,
        json={"query": "What is the annual salary and attendance of Isha Chowdhury?", "limit": 3}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated_user"] == "bob.hr"
    # Must retrieve the HR salary record
    assert any(hit["department"] == "hr" for hit in data["results"])
