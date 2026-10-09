import os
import json
import time
import uuid
from typing import Optional, Dict, Any, List
import lancedb
from sentence_transformers import SentenceTransformer

class ConversationMemory:
    """
    Continual conversation memory and local learning engine.
    1. Persists every conversation session and turn to disk (JSONL).
    2. Vectorizes user questions and verified responses into LanceDB.
    3. Provides instant semantic cache hits (<10ms) for previously discussed topics.
    4. Exports training datasets (ChatML/Alpaca format) for continual model fine-tuning.
    """
    def __init__(self, db_path="data/lancedb", storage_dir="data/conversations", training_dir="data/training"):
        self.storage_dir = os.path.abspath(storage_dir)
        self.training_dir = os.path.abspath(training_dir)
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.training_dir, exist_ok=True)
        
        self.log_file = os.path.join(self.storage_dir, "conversation_history.jsonl")
        self.training_export_file = os.path.join(self.training_dir, "planetarium_continual_train.jsonl")
        
        os.makedirs(db_path, exist_ok=True)
        self.db = lancedb.connect(db_path)
        self.table_name = "conversation_memory"
        
        # Load embedding model for fast semantic matching
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        self._ensure_table()

    def _ensure_table(self):
        """Ensures the conversation_memory table exists in LanceDB."""
        if self.table_name not in self.db.table_names():
            dummy_vec = self.encoder.encode("Cosmology observation", convert_to_numpy=True).tolist()
            initial_data = [{
                "id": "seed-000",
                "question": "What is the Milky Way?",
                "answer": "The Milky Way is a barred spiral galaxy containing hundreds of billions of stars, including our solar system.",
                "vector": dummy_vec,
                "timestamp": time.time(),
                "use_count": 1
            }]
            self.table = self.db.create_table(self.table_name, data=initial_data)
        else:
            self.table = self.db.open_table(self.table_name)

    def save_turn(self, question: str, answer: str, turn_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Saves a completed conversational turn to persistent JSONL log, 
        vectorizes it into LanceDB for instant future retrieval, and 
        appends to continual training dataset.
        """
        clean_q = question.strip()
        clean_a = answer.strip()
        if not clean_q or not clean_a:
            return {}

        record_id = turn_id or str(uuid.uuid4())
        record = {
            "id": record_id,
            "question": clean_q,
            "answer": clean_a,
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # 1. Append to local conversation log
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"[ConversationMemory] Error logging conversation: {e}", flush=True)

        # 2. Vectorize and ingest into LanceDB for immediate memory recall
        try:
            vec = self.encoder.encode(clean_q, convert_to_numpy=True).tolist()
            data = [{
                "id": record_id,
                "question": clean_q,
                "answer": clean_a,
                "vector": vec,
                "timestamp": record["timestamp"],
                "use_count": 1
            }]
            self.table.add(data)
            print(f"[ConversationMemory] Learned & indexed Q&A: '{clean_q[:40]}...'", flush=True)
        except Exception as e:
            print(f"[ConversationMemory] Error adding vector memory: {e}", flush=True)

        # 3. Export to continual fine-tuning dataset
        self._export_training_sample(clean_q, clean_a)
        return record

    def _export_training_sample(self, question: str, answer: str):
        """Appends formatted training sample in ChatML/Llama 3 instruction format."""
        try:
            sample = {
                "messages": [
                    {"role": "system", "content": "You are PlanetariumAI, a concise and knowledgeable astronomy assistant."},
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer}
                ]
            }
            with open(self.training_export_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(sample) + "\n")
        except Exception as e:
            print(f"[ConversationMemory] Error exporting training sample: {e}", flush=True)

    def find_cached_response(self, question: str, similarity_threshold: float = 0.90) -> Optional[str]:
        """
        Checks if a user question semantically matches a previously answered question.
        Returns the learned answer in <5ms if confidence meets the threshold.
        """
        if not question.strip():
            return None
        try:
            query_vec = self.encoder.encode(question.strip(), convert_to_numpy=True).tolist()
            results = self.table.search(query_vec).limit(1).to_list()
            if results:
                top = results[0]
                # LanceDB L2 distance: smaller is closer (squared L2 distance < 0.2 is very high similarity)
                distance = top.get("_distance", 1.0)
                if distance < (1.0 - similarity_threshold) * 2.0 or distance < 0.18:
                    print(f"[ConversationMemory] Instant memory hit! Distance: {distance:.3f} for query: '{question}'", flush=True)
                    return top["answer"]
        except Exception as e:
            print(f"[ConversationMemory] Search error: {e}", flush=True)
        return None
