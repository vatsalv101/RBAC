"""
Batch Ingestion Pipeline
Loads all FinSolve documents, generates embeddings, and indexes them in the VectorEngine.
"""
from typing import List, Dict, Any
from src.ingestion.chunker import DocumentChunker
from src.core.embedder import Embedder
from src.vector_store.engine import VectorEngine


class IngestionPipeline:
    def __init__(self, vector_engine: VectorEngine, embedder: Embedder):
        self.vector_engine = vector_engine
        self.embedder = embedder
        self.chunker = DocumentChunker()

    def run_ingestion(self) -> int:
        """
        Executes full ingestion:
        1. Chunks all files in data/
        2. Vectorizes chunk texts
        3. Upserts points into vector engine
        Returns total number of chunks indexed.
        """
        print("1. Discovering and chunking all files in data/...")
        chunks = self.chunker.chunk_all_documents()
        total_chunks = len(chunks)
        print(f"   Found {total_chunks} total chunks.")

        if total_chunks == 0:
            print("No chunks found to index.")
            return 0

        # 2. Extract texts for batch embedding
        texts = [chunk["text"] for chunk in chunks]
        print(f"2. Generating embeddings for {total_chunks} chunks via FastEmbed...")
        vectors = self.embedder.embed_texts(texts, batch_size=64)

        # 3. Assemble points for VectorEngine
        # Qdrant accepts integer or UUID IDs; we use the numerical index and store chunk_id in payload
        points: List[Dict[str, Any]] = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors), start=1):
            points.append({
                "id": idx,
                "vector": vector,
                "payload": chunk["payload"]
            })

        # 4. Upsert into VectorEngine
        print(f"3. Upserting {len(points)} chunks into VectorEngine...")
        self.vector_engine.upsert_chunks(points)
        print("All chunks successfully indexed with RBAC metadata!")

        return total_chunks


if __name__ == "__main__":
    # Initialize engine and embedder
    embedder = Embedder()
    engine = VectorEngine(
    location="",
    api_key=""
    )
    engine.initialize_collection(vector_dim=embedder.vector_dim)

    pipeline = IngestionPipeline(vector_engine=engine, embedder=embedder)
    count = pipeline.run_ingestion()
    print(f"\nPipeline run complete: {count} chunks indexed.")