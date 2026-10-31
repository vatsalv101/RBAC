import pytest
from src.vector_store.engine import VectorEngine


def test_rbac_vector_search():
    # 1. Open our in-memory filing cabinet (using simple 4-number vectors for testing)
    engine = VectorEngine(location=":memory:")
    engine.initialize_collection(vector_dim=4)

    # 2. Put TWO documents into the cabinet:
    # Notice: both documents have the exact same vector [1.0, 0.0, 0.0, 0.0],
    # so by default a normal search would find BOTH.
    # Only our RBAC bouncer can keep them separate!
    engine.upsert_chunks([
        {
            "id": 1,
            "vector": [1.0, 0.0, 0.0, 0.0],
            "payload": {
                "text": "FinSolve 2024 EBITDA grew by 25% with $50M operating cash flow.",
                "department": "finance",
                "allowed_roles": ["Finance", "C-Level"]
            }
        },
        {
            "id": 2,
            "vector": [1.0, 0.0, 0.0, 0.0],
            "payload": {
                "text": "Executive payroll: CEO Base Salary $850k + Bonus.",
                "department": "hr",
                "allowed_roles": ["HR", "C-Level"]
            }
        }
    ])

    query_vector = [1.0, 0.0, 0.0, 0.0]

    # TEST 1: A user with role "Finance" searches
    # Must only get the Finance document!
    finance_results = engine.search_with_rbac(query_vector=query_vector, user_roles=["Finance"])
    assert len(finance_results) == 1
    assert finance_results[0]["department"] == "finance"

    # TEST 2: A user with role "HR" searches
    # Must only get the HR document!
    hr_results = engine.search_with_rbac(query_vector=query_vector, user_roles=["HR"])
    assert len(hr_results) == 1
    assert hr_results[0]["department"] == "hr"

    # TEST 3: The CEO / C-Level searches
    # Must get BOTH documents!
    clevel_results = engine.search_with_rbac(query_vector=query_vector, user_roles=["C-Level"])
    assert len(clevel_results) == 2

    # TEST 4: A general "Employee" searches
    # Must get 0 documents because both are confidential!
    employee_results = engine.search_with_rbac(query_vector=query_vector, user_roles=["Employee"])
    assert len(employee_results) == 0