"""
Unit tests for Document Chunker and RBAC Metadata Inheritance.
Ensures every chunk generated across all department files is valid, non-empty,
and correctly inherits its parent document's RBAC security attributes.
"""
from pathlib import Path
import pytest
from src.ingestion.chunker import DocumentChunker

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


@pytest.fixture
def chunker():
    """Pytest fixture: provides a reusable DocumentChunker instance."""
    return DocumentChunker(max_chunk_chars=1200, chunk_overlap=150)


def test_chunk_all_documents_non_empty(chunker):
    """Verify that chunking data/ produces a substantial number of valid chunks."""
    chunks = chunker.chunk_all_documents()

    # We expect well over 100 chunks (100 HR rows alone, plus all markdown sections)
    assert len(chunks) > 120, f"Expected >120 chunks, but got {len(chunks)}"

    # Check chunk ID uniqueness: Vector DBs overwrite points with duplicate IDs!
    chunk_ids = [c["chunk_id"] for c in chunks]
    assert len(chunk_ids) == len(set(chunk_ids)), "Found duplicate chunk_ids!"


def test_rbac_metadata_inheritance_on_all_chunks(chunker):
    """Verify that every single chunk retains its critical RBAC security payload."""
    chunks = chunker.chunk_all_documents()

    for chunk in chunks:
        # Every chunk must have text
        assert len(chunk["text"].strip()) > 0, f"Empty text in chunk: {chunk['chunk_id']}"

        # Every chunk must have a payload with RBAC controls
        payload = chunk["payload"]
        assert "allowed_roles" in payload, f"Missing allowed_roles in {chunk['chunk_id']}"
        assert len(payload["allowed_roles"]) > 0, f"allowed_roles cannot be empty in {chunk['chunk_id']}"
        assert "department" in payload
        assert "doc_id" in payload
        assert "classification_level" in payload
        assert "contains_pii" in payload


def test_hr_csv_chunking_and_pii_flag(chunker):
    """Verify that the HR CSV is chunked into 100 employee records with PII flagged True."""
    hr_file = DATA_DIR / "hr" / "hr_data.csv"
    hr_chunks = chunker.chunk_csv(hr_file)

    # hr_data.csv has exactly 100 employee rows
    assert len(hr_chunks) == 100, f"Expected exactly 100 HR chunks, got {len(hr_chunks)}"

    for chunk in hr_chunks:
        payload = chunk["payload"]
        assert payload["department"] == "hr"
        assert payload["contains_pii"] is True
        assert payload["classification_level"] == "strictly_confidential_pii"
        assert payload["allowed_roles"] == ["HR", "C-Level"]
        # Verify employee_id was captured
        assert "employee_id" in payload
        assert payload["employee_id"].startswith("FINEMP")


def test_general_handbook_chunking_public_roles(chunker):
    """Verify Employee Handbook chunks are accessible to all roles and have no PII."""
    handbook_file = DATA_DIR / "general" / "employee_handbook.md"
    handbook_chunks = chunker.chunk_markdown(handbook_file)

    assert len(handbook_chunks) > 0

    for chunk in handbook_chunks:
        payload = chunk["payload"]
        assert payload["department"] == "general"
        assert payload["contains_pii"] is False
        assert payload["classification_level"] == "internal_public"
        # Must include standard Employee role so regular staff can query it
        assert "Employee" in payload["allowed_roles"]