"""
ChromaDB Store — Semantic vector storage for drone surveillance frames.

Enables natural language queries like "show me suspicious nighttime activity"
by embedding frame descriptions and performing similarity search.

Supports two modes:
  - Cloud mode: Connects to Chroma Cloud (api.trychroma.com) when credentials are set
  - Local mode: Falls back to local PersistentClient for offline/development use
"""

import chromadb
from chromadb.config import Settings
from config import (
    CHROMA_DB_PATH, CHROMA_COLLECTION_NAME, ensure_data_dir,
    CHROMA_CLOUD_ENABLED, CHROMA_HOST, CHROMA_API_KEY,
    CHROMA_TENANT, CHROMA_DATABASE,
)


class ChromaStore:
    """ChromaDB-based semantic search for security frame descriptions."""

    def __init__(self, db_path: str = None, collection_name: str = None,
                 use_cloud: bool = None):
        """
        Initialize ChromaDB client.

        Args:
            db_path: Local storage path (ignored in cloud mode)
            collection_name: Name of the ChromaDB collection
            use_cloud: Force cloud mode on/off. Defaults to auto-detect from env.
        """
        self.db_path = db_path or CHROMA_DB_PATH
        self.collection_name = collection_name or CHROMA_COLLECTION_NAME
        self.use_cloud = use_cloud if use_cloud is not None else CHROMA_CLOUD_ENABLED

        if self.use_cloud:
            # Connect to Chroma Cloud
            self.client = chromadb.HttpClient(
                host=CHROMA_HOST,
                port=443,
                ssl=True,
                headers={"x-chroma-token": CHROMA_API_KEY},
                tenant=CHROMA_TENANT,
                database=CHROMA_DATABASE,
            )
            print(f"[ChromaDB] Connected to cloud: {CHROMA_HOST} (db: {CHROMA_DATABASE})")
        else:
            # Fallback to local persistent storage
            ensure_data_dir()
            self.client = chromadb.PersistentClient(path=self.db_path)
            print(f"[ChromaDB] Using local storage: {self.db_path}")

        # Get or create collection — uses ChromaDB's default embedding function
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Drone surveillance frame descriptions for semantic search"}
        )

    def add_frame(self, frame_id: int, timestamp: str, location: str,
                  description: str, event_type: str = "",
                  risk_level: str = "", objects_detected: str = "") -> bool:
        """
        Add a frame description to the vector store.

        Args:
            frame_id: Unique frame identifier
            timestamp: Time in HH:MM format
            location: Patrol location name
            description: Rich text description of the frame
            event_type: Classified event type
            risk_level: Risk classification
            objects_detected: Comma-separated list of detected objects

        Returns:
            True if added successfully
        """
        try:
            # Build a rich document for embedding
            document = (
                f"Time: {timestamp}. Location: {location}. "
                f"{description} "
                f"Event type: {event_type}. Risk level: {risk_level}. "
                f"Objects: {objects_detected}."
            )

            self.collection.upsert(
                ids=[str(frame_id)],
                documents=[document],
                metadatas=[{
                    "frame_id": frame_id,
                    "timestamp": timestamp,
                    "location": location,
                    "event_type": event_type,
                    "risk_level": risk_level,
                    "objects_detected": objects_detected,
                    "raw_description": description,
                }]
            )
            return True
        except Exception as e:
            print(f"ChromaDB add error: {e}")
            return False

    def semantic_search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Perform semantic search across all stored frames.

        Args:
            query: Natural language query (e.g., "suspicious nighttime activity")
            top_k: Number of results to return

        Returns:
            List of matching frame dicts with similarity scores
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, self.collection.count()) if self.collection.count() > 0 else 1,
            )

            formatted = []
            if results and results["ids"] and results["ids"][0]:
                for i, frame_id in enumerate(results["ids"][0]):
                    entry = {
                        "frame_id": int(frame_id),
                        "document": results["documents"][0][i] if results["documents"] else "",
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                    }
                    if results["metadatas"] and results["metadatas"][0]:
                        entry.update(results["metadatas"][0][i])
                    formatted.append(entry)

            return formatted
        except Exception as e:
            print(f"ChromaDB search error: {e}")
            return []

    def get_similar_frames(self, frame_id: int, top_k: int = 3) -> list[dict]:
        """Find frames similar to a given frame."""
        try:
            # Get the frame's document
            result = self.collection.get(ids=[str(frame_id)])
            if not result or not result["documents"]:
                return []

            doc = result["documents"][0]
            # Search for similar, excluding self
            results = self.semantic_search(doc, top_k=top_k + 1)
            return [r for r in results if r["frame_id"] != frame_id][:top_k]
        except Exception as e:
            print(f"ChromaDB similarity error: {e}")
            return []

    def get_frame_count(self) -> int:
        """Get the total number of indexed frames."""
        return self.collection.count()

    def clear_all(self):
        """Delete and recreate the collection — for testing."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Drone surveillance frame descriptions for semantic search"}
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # ChromaDB clients handle cleanup automatically
