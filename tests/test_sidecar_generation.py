import json
from pathlib import Path
import pytest
from src.ingestion.sidecar_schema import BedrockSidecarMetadata

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def test_all_data_files_have_valid_sidecars():
    """Verify every content file in data/ has a valid, parseable .metadata.json sidecar."""
    # Find all content files (excluding .metadata.json files themselves)
    content_files = [
        f for f in DATA_DIR.rglob("*")
        if f.is_file() and not f.name.endswith(".metadata.json")
    ]

    assert len(content_files) >= 10, f"Expected at least 10 data files, found {len(content_files)}"

    for file_path in content_files:
        sidecar_path = file_path.with_name(f"{file_path.name}.metadata.json")
        assert sidecar_path.exists(), f"Missing sidecar for {file_path.relative_to(BASE_DIR)}"

        # Verify the sidecar matches the Pydantic schema
        with open(sidecar_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        # This will raise a ValidationError if the sidecar structure or roles are invalid
        validated_sidecar = BedrockSidecarMetadata.model_validate(raw_data)
        assert len(validated_sidecar.metadataAttributes.allowed_roles) > 0
        assert validated_sidecar.metadataAttributes.department in [
            "finance", "hr", "engineering", "marketing", "general"
        ]