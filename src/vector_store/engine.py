"""
Vector Engine Manager (In-Memory Local Mode + Cloud Parity)
Enforces RBAC pre-filtering at the index layer using scalar payload indexing.
"""
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest


class VectorEngine:
    def __init__(self, location: str = ":memory:", collection_name: str = "finsolve_enterprise_rag"):
        """
        location: ':memory:' for zero-dependency local testing,
                  or a cloud URL (e.g. 'https://xyz.qdrant.tech') when ready for cloud.
        """
        self.location = location
        self.collection_name = collection_name
        self.client = QdrantClient(location=location)

    def initialize_collection(self, vector_dim: int = 4):
        """
        Creates collection and sets up payload indexes for RBAC.
        """
        # 1. Create Collection with Cosine distance
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=rest.VectorParams(
                size=vector_dim,
                distance=rest.Distance.COSINE
            )
        )

        # 2. CREATE SCALAR PAYLOAD INDEXES (for cloud deployment)
        if self.location != ":memory:":
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="allowed_roles",
                field_schema=rest.PayloadSchemaType.KEYWORD
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="department",
                field_schema=rest.PayloadSchemaType.KEYWORD
            )

    def upsert_chunks(self, points: List[Dict[str, Any]]):
        """
        Inserts chunks into the vector store.
        Each point has: id, vector, and payload (text + metadata).
        """
        qdrant_points = [
            rest.PointStruct(
                id=p["id"],
                vector=p["vector"],
                payload=p["payload"]
            )
            for p in points
        ]
        self.client.upsert(
            collection_name=self.collection_name,
            points=qdrant_points
        )

    def search_with_rbac(
        self,
        query_vector: List[float],
        user_roles: List[str],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Executes strict RBAC PRE-FILTERED search.
        Uses modern Qdrant query_points.
        """
        # If user is C-Level, they have global access (no filter needed)
        rbac_filter = None
        if "C-Level" not in user_roles:
            rbac_filter = rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="allowed_roles",
                        match=rest.MatchAny(any=user_roles)
                    )
                ]
            )

        # Modern Qdrant API: query_points
        search_result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=rbac_filter,
            limit=limit
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "text": hit.payload.get("text"),
                "department": hit.payload.get("department"),
                "allowed_roles": hit.payload.get("allowed_roles")
            }
            for hit in search_result.points
        ]