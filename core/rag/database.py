import os
import functools
from typing import Optional, List
import lancedb
from sentence_transformers import SentenceTransformer
from .conversation_memory import ConversationMemory

import sys

def resolve_db_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    env_dir = os.environ.get("PLANETARIUM_DATA_DIR")
    if env_dir:
        cand = os.path.join(env_dir, "lancedb") if not env_dir.endswith("lancedb") else env_dir
        if os.path.exists(cand):
            return cand
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    c1 = os.path.join(base_dir, path)
    if os.path.exists(c1):
        return c1
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        for cand in [
            os.path.join(exe_dir, path),
            os.path.join(exe_dir, "resources", path),
            os.path.join(exe_dir, "..", "Resources", path)
        ]:
            if os.path.exists(cand):
                return cand
    return c1

class KnowledgeBase:
    """
    High-performance, low-latency planetarium knowledge engine.
    - Connects to LanceDB tables: 'astronomy_facts', 'astronomy_knowledge' (100k Q&A dataset),
      and 'conversation_memory' (continual learning).
    - Features sub-10ms Instant Semantic Cache for frequently asked cosmology questions.
    """
    def __init__(self, db_path="data/lancedb"):
        db_path = resolve_db_path(db_path)
        os.makedirs(db_path, exist_ok=True)
        self.db = lancedb.connect(db_path)
        print("Loading Embedding model (all-MiniLM-L6-v2)...", flush=True)
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        self.table_name = "astronomy_facts"
        self.knowledge_table_name = "astronomy_knowledge"
        
        # Initialize conversation memory for persistent learning
        self.memory = ConversationMemory(db_path=db_path)
        
    def init_table(self):
        pass
            
    def insert_facts(self, facts: list[str]):
        embeddings = self.encoder.encode(facts, convert_to_numpy=True).tolist()
        data = [
            {"id": str(i), "text": fact, "vector": emb} 
            for i, (fact, emb) in enumerate(zip(facts, embeddings))
        ]
        
        if self.table_name in self.db.table_names():
            self.db.drop_table(self.table_name)
            
        self.db.create_table(self.table_name, data=data)
        print(f"Inserted {len(facts)} facts into LanceDB.", flush=True)

    def get_instant_match(self, query: str, max_distance: float = 0.18) -> Optional[str]:
        """
        Sub-10ms Instant Semantic Cache Lookup.
        If the user asks a question matching previously learned conversations
        or the 100,000 curated planetarium questions, returns the validated answer 
        directly, delivering immediate millisecond response latency.
        """
        clean_q = query.strip()
        if not clean_q or len(clean_q) < 3:
            return None

        # 1. Check learned conversation memory first
        learned_ans = self.memory.find_cached_response(clean_q)
        if learned_ans:
            return learned_ans

        # 2. Check 100k Cosmology Knowledge Table
        if self.knowledge_table_name in self.db.table_names():
            try:
                table = self.db.open_table(self.knowledge_table_name)
                query_vec = self.encoder.encode(clean_q, convert_to_numpy=True).tolist()
                results = table.search(query_vec).limit(1).to_list()
                if results:
                    top = results[0]
                    dist = top.get("_distance", 1.0)
                    if dist <= max_distance:
                        print(f"[KnowledgeBase] Instant 100k Cache Hit! (Distance: {dist:.3f}) Question: '{top.get('question')}'", flush=True)
                        return top.get("answer")
            except Exception as e:
                print(f"[KnowledgeBase] Knowledge table search error: {e}", flush=True)

        return None
        
    def search(self, query: str, top_k: int = 3) -> list[str]:
        """
        Retrieves top relevant factual context from astronomical facts
        and the 100k knowledge base for LLM reasoning.
        """
        facts = []
        clean_q = query.strip()
        if not clean_q:
            return facts

        query_embedding = self.encoder.encode(clean_q, convert_to_numpy=True).tolist()
        
        # Search astronomy_facts
        if self.table_name in self.db.table_names():
            try:
                table = self.db.open_table(self.table_name)
                results = table.search(query_embedding).limit(top_k).to_list()
                facts.extend([res["text"] for res in results if "text" in res])
            except Exception as e:
                print(f"RAG search error in facts: {e}", flush=True)

        # Also search astronomy_knowledge if available for additional context
        if len(facts) < top_k and self.knowledge_table_name in self.db.table_names():
            try:
                ktable = self.db.open_table(self.knowledge_table_name)
                kresults = ktable.search(query_embedding).limit(top_k - len(facts)).to_list()
                for kr in kresults:
                    ans = kr.get("answer")
                    if ans and ans not in facts:
                        facts.append(ans)
            except Exception as e:
                print(f"RAG search error in knowledge: {e}", flush=True)
                
        return facts
