"""
Modular Embedding Provider
Generates semantic vectors for documents and queries.
Runs locally via FastEmbed with zero external API dependencies.
"""
from typing import List
from fastembed import TextEmbedding


class Embedder:
    """Generates 384-dimensional dense vectors using local ONNX runtime."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        self._model = TextEmbedding(model_name=self.model_name)
        self.vector_dim = 384  # bge-small produces 384-dimensional embeddings

    def embed_texts(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        """Embeds a list of document chunks into vectors."""
        if not texts:
            return []
        embeddings = list(self._model.embed(texts, batch_size=batch_size))
        return [emb.tolist() for emb in embeddings]

    def embed_query(self, query: str) -> List[float]:
        """Embeds a single search query into a vector."""
        return list(self._model.embed([query]))[0].tolist()


if __name__ == "__main__":
    embedder = Embedder()
    test_vec = embedder.embed_query("What is the leave policy?")
    print(f"Embedding successful! Vector dimensions: {len(test_vec)}")