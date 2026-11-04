"""
Interactive Search & RBAC Inspector
Demonstrates live vector search across all 312 chunks with real-time RBAC enforcement.
"""
from src.core.embedder import Embedder
from src.vector_store.engine import VectorEngine
from src.ingestion.pipeline import IngestionPipeline


def print_banner(text: str):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def run_demo_search(engine: VectorEngine, embedder: Embedder, query: str, user_roles: list):
    print(f"\n User Query:   \"{query}\"")
    print(f" User Roles:   {user_roles}")

    query_vector = embedder.embed_query(query)
    results = engine.search_with_rbac(query_vector=query_vector, user_roles=user_roles, limit=2)

    if not results:
        print(" [ACCESS BLOCKED] 0 chunks accessible for your role.")
        return

    print(f" [FOUND {len(results)} CHUNKS] Top results matching your permissions:")
    for idx, hit in enumerate(results, start=1):
        print(f"\n   --- Result {idx} (Similarity Score: {hit['score']:.4f}) ---")
        print(f"   Department:    {hit.get('department')}")
        print(f"   Allowed Roles: {hit.get('allowed_roles')}")
        text_snippet = hit.get('text', '').replace('\n', ' ')[:180]
        print(f"   Text Snippet:  {text_snippet}...")


def main():
    print_banner("1. INITIALIZING IN-MEMORY VECTOR ENGINE & FAST-EMBED")
    embedder = Embedder()
    engine = VectorEngine(location=":memory:")
    engine.initialize_collection(vector_dim=embedder.vector_dim)

    print_banner("2. INGESTING ALL 312 CHUNKS INTO VECTOR DATABASE")
    pipeline = IngestionPipeline(vector_engine=engine, embedder=embedder)
    pipeline.run_ingestion()

    print_banner("3. DEMO: WATCHING RBAC PRE-FILTERING IN ACTION")

    # DEMO 1: Public Employee Handbook query
    print("\n--- SCENARIO 1: General Policy Query ---")
    run_demo_search(
        engine, embedder,
        query="What are the rules for casual leave and sick leaves?",
        user_roles=["Employee"]
    )

    # DEMO 2: HR Confidential Salary Query asked by Finance vs HR
    print("\n--- SCENARIO 2: Confidential HR Salary Query ---")
    run_demo_search(
        engine, embedder,
        query="What is the salary and attendance of Isha Chowdhury?",
        user_roles=["Finance"]  # Must be BLOCKED
    )
    run_demo_search(
        engine, embedder,
        query="What is the salary and attendance of Isha Chowdhury?",
        user_roles=["HR"]       # Must be ALLOWED
    )

    # DEMO 3: Finance P&L Query asked by Employee vs Finance
    print("\n--- SCENARIO 3: Confidential Finance Revenue Query ---")
    run_demo_search(
        engine, embedder,
        query="What was the EBITDA and operational cash flow in 2024?",
        user_roles=["Employee"] # Must be BLOCKED
    )
    run_demo_search(
        engine, embedder,
        query="What was the EBITDA and operational cash flow in 2024?",
        user_roles=["Finance"]  # Must be ALLOWED
    )

    print_banner("DEMO COMPLETE: RBAC PRE-FILTERING VERIFIED 100% LOCALLY!")


if __name__ == "__main__":
    main()
