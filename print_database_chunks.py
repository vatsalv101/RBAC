"""
Database & Chunk Inspector
Prints the exact internal records stored inside the Vector Database (Point ID, Vector, and Payload).
"""
import json
from src.core.embedder import Embedder
from src.vector_store.engine import VectorEngine
from src.ingestion.pipeline import IngestionPipeline


def print_separator(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def main():
    print_separator("1. INGESTING DATA INTO IN-MEMORY VECTOR STORE")
    embedder = Embedder()
    engine = VectorEngine(location=":memory:")
    engine.initialize_collection(vector_dim=embedder.vector_dim)

    pipeline = IngestionPipeline(vector_engine=engine, embedder=embedder)
    total = pipeline.run_ingestion()
    print(f"\n✅ Total records stored in database: {total}")

    print_separator("2. HOW A VECTOR DATABASE STORES DATA INTERNALLY")
    print("""
Every single item in the vector database is stored as a 'Point' containing:
  1. ID: Unique integer or UUID
  2. Vector: A list of 384 floating-point numbers representing sentence meaning
  3. Payload: A JSON dictionary with the text and RBAC permission tags
    """)

    # Use Qdrant's scroll API to inspect raw points directly from the database
    # (scroll is like SELECT * in SQL, fetching raw database points)
    records, _ = engine.client.scroll(
        collection_name=engine.collection_name,
        limit=5,
        with_payload=True,
        with_vectors=True  # Fetch the actual numbers!
    )

    print_separator("3. RAW SAMPLES STORED IN THE DATABASE")

    for i, point in enumerate(records, start=1):
        print(f"\n>>> DATABASE POINT #{i} (Internal Point ID: {point.id})")
        print("-" * 75)

        # 1. The Vector
        vec_sample = [round(v, 4) for v in point.vector[:6]]
        print(f"🔹 VECTOR (384 numbers): {vec_sample} ... [and 378 more numbers]")

        # 2. The RBAC Payload (Sticky Note)
        payload = point.payload
        print("🔹 RBAC PAYLOAD (METADATA):")
        print(f"   - Chunk ID:             {payload.get('chunk_id')}")
        print(f"   - Department:           {payload.get('department')}")
        print(f"   - Allowed Roles:        {payload.get('allowed_roles')}")
        print(f"   - Classification Level: {payload.get('classification_level')}")
        print(f"   - Contains PII:         {payload.get('contains_pii')}")
        print(f"   - Source File:          {payload.get('source_uri')}")

        # 3. The Actual Text
        print("🔹 STORED TEXT CONTENT:")
        text_lines = payload.get('text', '').strip().split('\n')
        # Print first few lines of text
        for line in text_lines[:5]:
            print(f"     {line}")
        if len(text_lines) > 5:
            print(f"     ... [{len(text_lines) - 5} more lines]")

    # Department breakdown
    all_records, _ = engine.client.scroll(
        collection_name=engine.collection_name,
        limit=500,
        with_payload=True,
        with_vectors=False
    )
    dept_counts = {}
    for r in all_records:
        dept = r.payload.get("department", "unknown")
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

    print_separator("4. DATABASE CONTENT BREAKDOWN BY DEPARTMENT")
    for dept, count in sorted(dept_counts.items()):
        print(f"  • Department: {dept.upper():<15} | Stored Chunks: {count}")
    print(f"\n  TOTAL STORED CHUNKS: {len(all_records)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
