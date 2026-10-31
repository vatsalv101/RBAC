"""
Bedrock Sidecar Metadata Schema (Pydantic v2)
Directly mirrors AWS Bedrock Knowledge Bases S3 DataSource sidecar specifications:
<filename>.<ext>.metadata.json
"""
import re
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


# Valid FinSolve enterprise departments
DepartmentType = Literal["finance", "hr", "engineering", "marketing", "general"]

# Data classification levels for FinTech compliance (SOC2 / GDPR)
ClassificationType = Literal[
    "internal_public",        # e.g., Employee Handbook, general FAQs
    "internal",               # e.g., Marketing performance reports
    "internal_restricted",    # e.g., Engineering architecture & microservices
    "confidential",           # e.g., Financial summaries, P&L statements
    "strictly_confidential_pii" # e.g., HR salary, performance, date of birth
]

VALID_RBAC_ROLES = {"Employee", "Finance", "HR", "Engineering", "Marketing", "C-Level"}


class BedrockMetadataAttributes(BaseModel):
    """
    Attributes mapped 1:1 to AWS Bedrock 'metadataAttributes'.
    AWS Bedrock supports STRING, NUMBER, BOOLEAN, and STRING_LIST.
    """
    doc_id: str = Field(
        ...,
        pattern=r"^[A-Z0-9\-_]{3,64}$",
        description="Deterministic business ID for document lineage (e.g. FIN-2024-SUMM)"
    )
    department: DepartmentType = Field(
        ...,
        description="The owning department silo"
    )
    allowed_roles: List[str] = Field(
        ...,
        min_length=1,
        description="STRING_LIST of roles authorized to retrieve chunks of this document"
    )
    classification_level: ClassificationType = Field(
        ...,
        description="Data classification level for security audits"
    )
    fiscal_year: int = Field(
        default=2024,
        ge=2000,
        le=2100,
        description="Fiscal year for temporal filtering"
    )
    contains_pii: bool = Field(
        default=False,
        description="Boolean flag for PII presence (triggers special masking if true)"
    )
    document_type: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Category of document (e.g. financial_summary, employee_handbook)"
    )
    source_uri: str = Field(
        ...,
        min_length=3,
        description="Local path (e.g. data/finance/financial_summary.md), file:// URI, or s3:// URI"
    )

    @field_validator("allowed_roles")
    @classmethod
    def validate_roles(cls, roles: List[str]) -> List[str]:
        """Ensure all roles in the list match FinSolve's recognized security principals."""
        for r in roles:
            if r not in VALID_RBAC_ROLES:
                raise ValueError(
                    f"Invalid role '{r}'. Must be one of: {sorted(list(VALID_RBAC_ROLES))}"
                )
        return roles


class BedrockSidecarMetadata(BaseModel):
    """
    Top-level wrapper matching the AWS Bedrock Knowledge Bases contract:
    {
      "metadataAttributes": { ... }
    }
    """
    metadataAttributes: BedrockMetadataAttributes

    def to_sidecar_json(self) -> str:
        """Exports formatted JSON ready to be written as <filename>.metadata.json."""
        return self.model_dump_json(indent=2)