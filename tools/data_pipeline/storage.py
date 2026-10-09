"""LanceDB vector storage and embedding for astronomy knowledge engine."""

import os
import uuid
from typing import Any, Dict, List, Optional
import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer


class KnowledgeStorage:
    """Manages text embedding and LanceDB vector ingestion for QA pairs."""

    def __init__(
        self,
        db_path: str = "data/lancedb",
        table_name: str = "astronomy_knowledge",
        embedding_model_name: str = "all-MiniLM-L6-v2"
    ):
        """Initialize LanceDB connection and embedding encoder."""
        self.db_path = os.path.abspath(db_path)
        os.makedirs(self.db_path, exist_ok=True)
        self.db = lancedb.connect(self.db_path)
        self.table_name = table_name

        print(f"[KnowledgeStorage] Loading embedding model '{embedding_model_name}'...")
        try:
            self.encoder = SentenceTransformer(embedding_model_name, trust_remote_code=True)
        except Exception as e:
            print(f"[KnowledgeStorage] Warning: Failed to load {embedding_model_name} ({e}). Falling back to 'all-MiniLM-L6-v2'.")
            self.encoder = SentenceTransformer("all-MiniLM-L6-v2")

        # Determine embedding dimension
        dummy_vec = self.encoder.encode("test", convert_to_numpy=True)
        self.vector_dim = int(dummy_vec.shape[0])
        print(f"[KnowledgeStorage] Embedding dimension: {self.vector_dim}")

    def ingest(self, records: List[Dict[str, Any]], mode: str = "overwrite") -> int:
        """Embed and ingest approved QA records into LanceDB."""
        if not records:
            print("[KnowledgeStorage] No records to ingest.")
            return 0

        # Extract texts for embedding (search against the question or combined text)
        texts_to_embed = [
            f"{r.get('question_text', '')} {r.get('answer_text', '')}".strip()
            for r in records
        ]

        print(f"[KnowledgeStorage] Generating embeddings for {len(texts_to_embed)} records...")
        embeddings = self.encoder.encode(texts_to_embed, convert_to_numpy=True).tolist()

        data = []
        for i, (rec, emb) in enumerate(zip(records, embeddings)):
            rec_id = str(rec.get("id") or str(uuid.uuid4()))
            data.append({
                "id": rec_id,
                "intent_category": str(rec.get("intent_category", "General")),
                "question_text": str(rec.get("question_text", "")),
                "answer_text": str(rec.get("answer_text", "")),
                "citation_source": str(rec.get("citation_source", "Unknown")),
                "vector": emb
            })

        # Define explicit PyArrow schema to guarantee structure
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("intent_category", pa.string()),
            pa.field("question_text", pa.string()),
            pa.field("answer_text", pa.string()),
            pa.field("citation_source", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), self.vector_dim))
        ])

        print(f"[KnowledgeStorage] Ingesting {len(data)} records into table '{self.table_name}' at '{self.db_path}'...")
        table = self.db.create_table(self.table_name, data=data, schema=schema, mode=mode)
        print(f"[KnowledgeStorage] Successfully ingested {len(table.to_arrow())} total records.")
        return len(data)

    def _table_exists(self) -> bool:
        """Check if target table exists in LanceDB."""
        try:
            res = self.db.list_tables()
            if hasattr(res, "tables"):
                return self.table_name in res.tables
            return self.table_name in list(res)
        except Exception:
            try:
                return self.table_name in self.db.table_names()
            except Exception:
                return False

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform vector similarity search against the knowledge database."""
        if not self._table_exists():
            print(f"[KnowledgeStorage] Table '{self.table_name}' does not exist.")
            return []

        query_vec = self.encoder.encode(query, convert_to_numpy=True).tolist()
        table = self.db.open_table(self.table_name)
        results = table.search(query_vec).limit(top_k).to_list()
        return results
