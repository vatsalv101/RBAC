"""
Sidecar Metadata Generator
Scans the data/ folder and generates AWS Bedrock-compliant <filename>.metadata.json
files for all department files using the Pydantic sidecar schema.
"""
from pathlib import Path
from typing import Dict, Any

from src.ingestion.sidecar_schema import (
    BedrockSidecarMetadata,
    BedrockMetadataAttributes,
)

# Root directory of the repository (D:\RBAC)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

# Mapping rules: Define the security policy for every file in the company
METADATA_CONFIG: Dict[str, Dict[str, Any]] = {
    # 1. General Documents (Public to all employees)
    "data/general/employee_handbook.md": {
        "doc_id": "GEN-HANDBOOK-2024",
        "department": "general",
        "allowed_roles": ["Employee", "Finance", "HR", "Engineering", "Marketing", "C-Level"],
        "classification_level": "internal_public",
        "fiscal_year": 2024,
        "contains_pii": False,
        "document_type": "employee_handbook",
    },
    # 2. Finance Documents (Only Finance & C-Level)
    "data/finance/financial_summary.md": {
        "doc_id": "FIN-SUMMARY-2024",
        "department": "finance",
        "allowed_roles": ["Finance", "C-Level"],
        "classification_level": "confidential",
        "fiscal_year": 2024,
        "contains_pii": False,
        "document_type": "financial_summary",
    },
    "data/finance/quarterly_financial_report.md": {
        "doc_id": "FIN-QTR-REPORT-2024",
        "department": "finance",
        "allowed_roles": ["Finance", "C-Level"],
        "classification_level": "confidential",
        "fiscal_year": 2024,
        "contains_pii": False,
        "document_type": "quarterly_financial_report",
    },
    # 3. Engineering Documents (Only Engineering & C-Level)
    "data/engineering/engineering_master_doc.md": {
        "doc_id": "ENG-MASTER-2024",
        "department": "engineering",
        "allowed_roles": ["Engineering", "C-Level"],
        "classification_level": "internal_restricted",
        "fiscal_year": 2024,
        "contains_pii": False,
        "document_type": "architecture_specification",
    },
    # 4. HR Documents (Strictly confidential PII - Only HR & C-Level)
    "data/hr/hr_data.csv": {
        "doc_id": "HR-PAYROLL-PII-2024",
        "department": "hr",
        "allowed_roles": ["HR", "C-Level"],
        "classification_level": "strictly_confidential_pii",
        "fiscal_year": 2024,
        "contains_pii": True,
        "document_type": "employee_records",
    },
    # 5. Marketing Documents (Only Marketing & C-Level)
    "data/marketing/marketing_report_2024.md": {
        "doc_id": "MKT-ANNUAL-2024",
        "department": "marketing",
        "allowed_roles": ["Marketing", "C-Level"],
        "classification_level": "internal",
        "fiscal_year": 2024,
        "contains_pii": False,
        "document_type": "marketing_annual_report",
    },
    "data/marketing/marketing_report_q1_2024.md": {
        "doc_id": "MKT-Q1-2024",
        "department": "marketing",
        "allowed_roles": ["Marketing", "C-Level"],
        "classification_level": "internal",
        "fiscal_year": 2024,
        "contains_pii": False,
        "document_type": "marketing_quarterly_report",
    },
    "data/marketing/marketing_report_q2_2024.md": {
        "doc_id": "MKT-Q2-2024",
        "department": "marketing",
        "allowed_roles": ["Marketing", "C-Level"],
        "classification_level": "internal",
        "fiscal_year": 2024,
        "contains_pii": False,
        "document_type": "marketing_quarterly_report",
    },
    "data/marketing/marketing_report_q3_2024.md": {
        "doc_id": "MKT-Q3-2024",
        "department": "marketing",
        "allowed_roles": ["Marketing", "C-Level"],
        "classification_level": "internal",
        "fiscal_year": 2024,
        "contains_pii": False,
        "document_type": "marketing_quarterly_report",
    },
    "data/marketing/market_report_q4_2024.md": {
        "doc_id": "MKT-Q4-2024",
        "department": "marketing",
        "allowed_roles": ["Marketing", "C-Level"],
        "classification_level": "internal",
        "fiscal_year": 2024,
        "contains_pii": False,
        "document_type": "marketing_quarterly_report",
    },
}


def generate_all_sidecars():
    """Generates sidecar .metadata.json files for all defined documents."""
    generated_count = 0

    for relative_path_str, config in METADATA_CONFIG.items():
        doc_path = BASE_DIR / relative_path_str

        if not doc_path.exists():
            print(f"⚠️ Warning: Target file {doc_path} not found. Skipping.")
            continue

        # 1. Instantiate Pydantic model (this validates that all roles and classifications are legal!)
        attributes = BedrockMetadataAttributes(
            doc_id=config["doc_id"],
            department=config["department"],
            allowed_roles=config["allowed_roles"],
            classification_level=config["classification_level"],
            fiscal_year=config["fiscal_year"],
            contains_pii=config["contains_pii"],
            document_type=config["document_type"],
            source_uri=relative_path_str.replace("\\", "/"),
        )
        sidecar = BedrockSidecarMetadata(metadataAttributes=attributes)

        # 2. Sidecar filename convention: <filename>.<ext>.metadata.json
        sidecar_path = doc_path.with_name(f"{doc_path.name}.metadata.json")

        # 3. Write formatted JSON to disk
        with open(sidecar_path, "w", encoding="utf-8") as f:
            f.write(sidecar.to_sidecar_json())

        print(f"✅ Generated: {sidecar_path.relative_to(BASE_DIR)}")
        generated_count += 1

    print(f"\n🎉 Successfully generated {generated_count} sidecar metadata files.")


if __name__ == "__main__":
    generate_all_sidecars()