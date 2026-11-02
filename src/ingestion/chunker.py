"""
Document Chunker with RBAC Metadata Inheritance.
Splits Markdown documents by semantic sections and CSV files by row records,
ensuring every chunk inherits the security metadata from its parent sidecar.
"""
import csv
import json
import re
from pathlib import Path
from typing import List, Dict, Any

from src.ingestion.sidecar_schema import BedrockSidecarMetadata

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


class DocumentChunker:
    """Chunks documents and stamps each chunk with RBAC security attributes."""

    def __init__(self, max_chunk_chars: int = 1200, chunk_overlap: int = 150):
        self.max_chunk_chars = max_chunk_chars
        self.chunk_overlap = chunk_overlap

    def load_sidecar(self, file_path: Path) -> Dict[str, Any]:
        """Loads and validates the sidecar metadata for a given file."""
        sidecar_path = file_path.with_name(f"{file_path.name}.metadata.json")
        if not sidecar_path.exists():
            raise FileNotFoundError(f"Sidecar missing for: {file_path}")

        with open(sidecar_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        validated = BedrockSidecarMetadata.model_validate(data)
        return validated.metadataAttributes.model_dump()

    def chunk_markdown(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Chunks markdown by header sections (##, ###) and splits long sections
        while preserving paragraph integrity.
        """
        metadata = self.load_sidecar(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split content along markdown headers (## or ###)
        sections = re.split(r"(?=(?:\n|^)#{1,3}\s)", content)
        chunks: List[Dict[str, Any]] = []
        chunk_index = 0

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # If section is small enough, keep it as one chunk
            if len(section) <= self.max_chunk_chars:
                chunks.append(self._create_chunk_record(section, metadata, chunk_index, file_path))
                chunk_index += 1
            else:
                # Split large section by paragraphs
                paragraphs = section.split("\n\n")
                current_text = ""

                for p in paragraphs:
                    p = p.strip()
                    if not p:
                        continue
                    if len(current_text) + len(p) + 2 <= self.max_chunk_chars:
                        current_text = f"{current_text}\n\n{p}" if current_text else p
                    else:
                        if current_text:
                            chunks.append(self._create_chunk_record(current_text, metadata, chunk_index, file_path))
                            chunk_index += 1
                        current_text = p

                if current_text:
                    chunks.append(self._create_chunk_record(current_text, metadata, chunk_index, file_path))
                    chunk_index += 1

        return chunks

    def chunk_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Chunks structured tabular data (HR CSV) into individual semantic records.
        Each employee row becomes a rich self-contained text chunk.
        """
        metadata = self.load_sidecar(file_path)
        chunks: List[Dict[str, Any]] = []

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                # Format the row into an easily readable text block for embedding
                text_repr = (
                    f"FinSolve Employee Record:\n"
                    f"- Employee ID: {row.get('employee_id')}\n"
                    f"- Full Name: {row.get('full_name')}\n"
                    f"- Department: {row.get('department')} | Role: {row.get('role')}\n"
                    f"- Email: {row.get('email')} | Location: {row.get('location')}\n"
                    f"- Date of Birth: {row.get('date_of_birth')} | Joining Date: {row.get('date_of_joining')}\n"
                    f"- Manager ID: {row.get('manager_id')}\n"
                    f"- Annual Salary: ₹{float(row.get('salary', 0)):,.2f}\n"
                    f"- Leave Balance: {row.get('leave_balance')} days (Leaves Taken: {row.get('leaves_taken')})\n"
                    f"- Attendance: {row.get('attendance_pct')}% | Performance Rating: {row.get('performance_rating')}/5\n"
                    f"- Last Review Date: {row.get('last_review_date')}"
                )

                chunk = self._create_chunk_record(text_repr, metadata, idx, file_path)
                # Extra attribute for specific employee lookup
                chunk["payload"]["employee_id"] = row.get("employee_id")
                chunks.append(chunk)

        return chunks

    def chunk_all_documents(self) -> List[Dict[str, Any]]:
        """Discovers all documents in data/ and produces a unified list of tagged chunks."""
        all_chunks: List[Dict[str, Any]] = []

        for file_path in sorted(DATA_DIR.rglob("*")):
            if not file_path.is_file() or file_path.name.endswith(".metadata.json"):
                continue

            if file_path.suffix.lower() == ".md":
                doc_chunks = self.chunk_markdown(file_path)
                all_chunks.extend(doc_chunks)
            elif file_path.suffix.lower() == ".csv":
                csv_chunks = self.chunk_csv(file_path)
                all_chunks.extend(csv_chunks)

        return all_chunks

    def _create_chunk_record(
        self,
        text: str,
        metadata: Dict[str, Any],
        chunk_index: int,
        source_file: Path
    ) -> Dict[str, Any]:
        """Creates a standardized chunk payload inheriting all RBAC permissions."""
        chunk_id = f"{metadata['doc_id']}_CHUNK_{chunk_index:04d}"
        return {
            "chunk_id": chunk_id,
            "text": text,
            "payload": {
                "chunk_id": chunk_id,
                "text": text,
                "doc_id": metadata["doc_id"],
                "department": metadata["department"],
                "allowed_roles": metadata["allowed_roles"],
                "classification_level": metadata["classification_level"],
                "fiscal_year": metadata["fiscal_year"],
                "contains_pii": metadata["contains_pii"],
                "document_type": metadata["document_type"],
                "source_uri": str(source_file.relative_to(BASE_DIR)).replace("\\", "/"),
            }
        }


if __name__ == "__main__":
    chunker = DocumentChunker()
    chunks = chunker.chunk_all_documents()
    print(f"🎉 Chunking complete! Generated {len(chunks)} total chunks.")

    # Show a preview of the first chunk
    if chunks:
        sample = chunks[0]
        print(f"\nSample Chunk ID: {sample['chunk_id']}")
        print(f"Department: {sample['payload']['department']}")
        print(f"Allowed Roles: {sample['payload']['allowed_roles']}")
        print(f"Contains PII: {sample['payload']['contains_pii']}")
        print(f"Text Preview:\n{sample['text'][:200]}...")