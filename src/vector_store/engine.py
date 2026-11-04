"""
Vector Engine Manager (Qdrant Cloud + Local Fallback)
Connects to managed cloud vector cluster with automatic scalar payload indexing.
"""
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

# Load environment variables from .env
load_dotenv()


class VectorEngine:
    def __init__(
        self,
        location: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: str = "finsolve_enterprise_rag"
    ):
        """
        If location == ':memory:', runs in local in-memory mode.
        If cloud URL & API key are present, connects to managed Qdrant Cloud.
        """
        self.collection_name = collection_name

        if location == ":memory:":
            print("[LOCAL] In-memory mode explicitly requested (:memory:)")
            self.client = QdrantClient(location=":memory:")
            self.is_cloud = False
            self.cloud_url = ":memory:"
            self.api_key = None
        elif (location or os.getenv("QDRANT_CLOUD_URL")) and (api_key or os.getenv("QDRANT_API_KEY")):
            self.cloud_url = location or os.getenv("QDRANT_CLOUD_URL")
            self.api_key = api_key or os.getenv("QDRANT_API_KEY")
            print(f"[CLOUD] Connecting to Managed Qdrant Cloud: {self.cloud_url}")
            self.client = QdrantClient(
                url=self.cloud_url,
                api_key=self.api_key,
                timeout=30.0
            )
            self.is_cloud = True
        else:
            print("[LOCAL] No cloud credentials found. Using local in-memory storage (:memory:)")
            self.client = QdrantClient(location=":memory:")
            self.is_cloud = False
            self.cloud_url = ":memory:"
            self.api_key = None

    def initialize_collection(self, vector_dim: int = 384):
        """
        Creates collection and configures real scalar payload indexes on the cloud cluster.
        """
        collections = [c.name for c in self.client.get_collections().collections]

        if self.collection_name not in collections:
            print(f"Creating collection '{self.collection_name}' (dim={vector_dim}, metric=Cosine)...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=rest.VectorParams(
                    size=vector_dim,
                    distance=rest.Distance.COSINE
                )
            )
            print(f"Collection '{self.collection_name}' created successfully.")
        else:
            print(f"Collection '{self.collection_name}' already exists.")

        # If on Cloud, create the inverted indexes for lightning-fast RBAC pre-filtering
        if self.is_cloud:
            self._create_cloud_payload_indexes()

    def _create_cloud_payload_indexes(self):
        """
        Creates inverted scalar payload indexes on the cloud cluster.
        Crucial for high-speed RBAC pre-filtering without full-table scans.
        """
        index_specs = [
            ("allowed_roles", rest.PayloadSchemaType.KEYWORD),
            ("department", rest.PayloadSchemaType.KEYWORD),
            ("classification_level", rest.PayloadSchemaType.KEYWORD),
            ("doc_id", rest.PayloadSchemaType.KEYWORD),
            ("fiscal_year", rest.PayloadSchemaType.INTEGER),
            ("contains_pii", rest.PayloadSchemaType.BOOL),
        ]
        for field, schema in index_specs:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field,
                field_schema=schema,
                wait=True
            )
        print("[SUCCESS] Cloud scalar payload indexes verified and active.")

    def upsert_chunks(self, points: List[Dict[str, Any]], batch_size: int = 64):
        """
        Batch-upserts chunks to the cloud vector store.
        """
        qdrant_points = [
            rest.PointStruct(
                id=p["id"],
                vector=p["vector"],
                payload=p["payload"]
            )
            for p in points
        ]

        total = len(qdrant_points)
        for i in range(0, total, batch_size):
            batch = qdrant_points[i : i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
                wait=True
            )
            print(f"   Uploaded batch {min(i + batch_size, total)}/{total} points...")

    def search_with_rbac(
        self,
        query_vector: List[float],
        user_roles: List[str],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Executes strict RBAC PRE-FILTERED search on the cloud database.
        """
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
