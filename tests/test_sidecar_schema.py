import json
import pytest
from pydantic import ValidationError
from src.ingestion.sidecar_schema import BedrockSidecarMetadata, BedrockMetadataAttributes


def test_valid_finance_sidecar():
    """Test generating a valid Finance sidecar metadata object."""
    sidecar = BedrockSidecarMetadata(
        metadataAttributes=BedrockMetadataAttributes(
            doc_id="FIN-2024-001",
            department="finance",
            allowed_roles=["Finance", "C-Level"],
            classification_level="confidential",
            fiscal_year=2024,
            contains_pii=False,
            document_type="financial_summary",
            source_uri="data/finance/financial_summary.md"
        )
    )
    json_output = sidecar.to_sidecar_json()
    data = json.loads(json_output)

    # Validate parsed JSON structure
    assert data["metadataAttributes"]["department"] == "finance"
    assert data["metadataAttributes"]["allowed_roles"] == ["Finance", "C-Level"]
    assert data["metadataAttributes"]["classification_level"] == "confidential"
    assert data["metadataAttributes"]["contains_pii"] is False


def test_invalid_role_rejection():
    """Verify that an unauthorized role name (e.g. 'HackerRole') is blocked by validation."""
    with pytest.raises(ValidationError):
        BedrockSidecarMetadata(
            metadataAttributes=BedrockMetadataAttributes(
                doc_id="FIN-2024-001",
                department="finance",
                allowed_roles=["HackerRole"],  # Must fail!
                classification_level="confidential",
                fiscal_year=2024,
                document_type="financial_summary",
                source_uri="data/finance/financial_summary.md"
            )
        )