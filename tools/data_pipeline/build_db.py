"""Standalone Astronomy Knowledge Engine Data Pipeline.

Orchestrates:
1. Seed Ingestion (CSV)
2. Synthetic Expansion (Question Variations via Local LLM)
3. Fact-Checking (LLM-as-a-judge Verification)
4. Vectorization & Ingestion (LanceDB)
"""

import argparse
import csv
import glob
import os
import sys
import time
from typing import Any, Dict, List, Optional

# Support running directly or as package
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from expander import SyntheticExpander
from verifier import FactChecker
from storage import KnowledgeStorage


def find_default_model() -> Optional[str]:
    """Auto-detect available GGUF model in core/models."""
    possible_dirs = [
        os.path.join(current_dir, "..", "..", "core", "models"),
        os.path.join(current_dir, "models"),
        "models"
    ]
    for d in possible_dirs:
        abs_d = os.path.abspath(d)
        if os.path.exists(abs_d):
            ggufs = glob.glob(os.path.join(abs_d, "*.gguf"))
            if ggufs:
                return ggufs[0]
    return None


def read_seed_csv(csv_path: str, max_facts: Optional[int] = None) -> List[Dict[str, str]]:
    """Read and validate the seed facts CSV."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Seed CSV not found at: {csv_path}")

    records = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required_cols = {"intent_category", "seed_fact", "citation_source"}
        if not required_cols.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"CSV must contain columns: {required_cols}. Found: {reader.fieldnames}")

        for row in reader:
            records.append({
                "intent_category": row["intent_category"].strip(),
                "seed_fact": row["seed_fact"].strip(),
                "citation_source": row["citation_source"].strip()
            })
            if max_facts and len(records) >= max_facts:
                break

    return records


def run_pipeline(
    csv_path: str,
    output_db: str,
    table_name: str = "astronomy_knowledge",
    model_path: Optional[str] = None,
    variations_per_fact: int = 2,
    max_facts: Optional[int] = None,
    use_mock_llm: bool = False,
    threads: int = 12,
    verify_query: str = "How many moons does Jupiter have?"
) -> Dict[str, Any]:
    """Execute the full 4-step knowledge pipeline."""
    start_time = time.time()
    print("=" * 70)
    print("      PLANETARIUM KNOWLEDGE ENGINE PIPELINE (PHASE 09)")
    print("=" * 70)

    # 1. Seed Ingestion
    print(f"\n[Step 1/4] Reading seed facts from '{csv_path}'...")
    seed_records = read_seed_csv(csv_path, max_facts=max_facts)
    print(f"[Step 1/4] Loaded {len(seed_records)} seed facts.")

    # 2. Setup LLM
    llm_instance = None
    if not use_mock_llm:
        resolved_model = model_path or find_default_model()
        if resolved_model and os.path.exists(resolved_model):
            print(f"\n[LLM] Initializing Llama inference engine from '{resolved_model}'...")
            try:
                from llama_cpp import Llama
                llm_instance = Llama(
                    model_path=resolved_model,
                    n_threads=threads,
                    n_ctx=512,
                    verbose=False
                )
                print("[LLM] Local reasoning model successfully loaded.")
            except Exception as e:
                print(f"[LLM] Warning: Failed to load Llama ({e}). Falling back to mock/heuristics.")
        else:
            print("[LLM] No GGUF model found. Using deterministic heuristic generator.")
    else:
        print("[LLM] Mock mode enabled explicitly.")

    expander = SyntheticExpander(llm=llm_instance)
    fact_checker = FactChecker(llm=llm_instance)

    # 3. Synthetic Expansion & Fact-Checking
    print(f"\n[Step 2 & 3/4] Generating question variations and running fact-checking...")
    approved_qa_pairs: List[Dict[str, Any]] = []
    total_generated = 0
    total_dropped = 0

    for idx, item in enumerate(seed_records, start=1):
        fact = item["seed_fact"]
        category = item["intent_category"]
        source = item["citation_source"]

        print(f"  [{idx}/{len(seed_records)}] Expanding: \"{fact[:60]}...\"", flush=True)
        questions = expander.generate_variations(fact, num_variations=variations_per_fact)
        total_generated += len(questions)

        for q in questions:
            is_valid = fact_checker.check_fact(question=q, answer=fact)
            if is_valid:
                approved_qa_pairs.append({
                    "id": f"fact_{idx}_{len(approved_qa_pairs)}",
                    "intent_category": category,
                    "question_text": q,
                    "answer_text": fact,
                    "citation_source": source
                })
            else:
                total_dropped += 1
                print(f"    [DROPPED] Fact-check FAIL for: \"{q}\"", flush=True)

    print(f"\n[Stats] Generated: {total_generated} | Passed: {len(approved_qa_pairs)} | Dropped: {total_dropped}", flush=True)

    # 4. Vectorization & Ingestion into LanceDB
    print(f"\n[Step 4/4] Ingesting approved QA pairs into LanceDB ('{output_db}')...")
    storage = KnowledgeStorage(db_path=output_db, table_name=table_name)
    ingested_count = storage.ingest(approved_qa_pairs, mode="overwrite")

    # 5. Database Verification / Test Search
    print(f"\n[Verification] Querying generated vector database with: \"{verify_query}\"...")
    search_results = storage.search(verify_query, top_k=3)
    print(f"[Verification] Found {len(search_results)} relevant matches:")
    for rank, res in enumerate(search_results, start=1):
        q_text = res.get("question_text", "")
        a_text = res.get("answer_text", "")
        cat = res.get("intent_category", "")
        src = res.get("citation_source", "")
        dist = res.get("_distance", 0.0)
        print(f"   Match #{rank} (Dist: {dist:.4f}) [{cat} | {src}]")
        print(f"     Q: {q_text}")
        print(f"     A: {a_text[:80]}...")

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"PIPELINE COMPLETE in {elapsed:.2f} seconds.")
    print(f"Total Seed Facts: {len(seed_records)}")
    print(f"Total QA Pairs Ingested: {ingested_count}")
    print(f"Target Database: {os.path.abspath(output_db)} (Table: {table_name})")
    print("=" * 70)

    return {
        "seed_count": len(seed_records),
        "generated_count": total_generated,
        "approved_count": len(approved_qa_pairs),
        "dropped_count": total_dropped,
        "ingested_count": ingested_count,
        "elapsed_seconds": elapsed,
        "search_results": search_results
    }


def main():
    parser = argparse.ArgumentParser(description="Planetarium Knowledge Engine Data Pipeline")
    parser.add_argument(
        "--csv",
        type=str,
        default=os.path.join(current_dir, "seed_facts.csv"),
        help="Path to input seed facts CSV"
    )
    parser.add_argument(
        "--output-db",
        type=str,
        default=os.path.join(current_dir, "output", "lancedb"),
        help="Path to target LanceDB directory"
    )
    parser.add_argument(
        "--table-name",
        type=str,
        default="astronomy_knowledge",
        help="LanceDB table name"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Path to GGUF reasoning model (defaults to core/models/*.gguf)"
    )
    parser.add_argument(
        "--variations-per-fact",
        type=int,
        default=2,
        help="Number of question variations to generate per seed fact"
    )
    parser.add_argument(
        "--max-facts",
        type=int,
        default=None,
        help="Limit number of seed facts to process"
    )
    parser.add_argument(
        "--mock-llm",
        action="store_true",
        help="Run without local LLM weights (uses deterministic expansion/verification)"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=12,
        help="Number of CPU threads for Llama"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="What is Jupiter's magnetic field like?",
        help="Verification query to test vector retrieval after build"
    )

    args = parser.parse_args()
    run_pipeline(
        csv_path=args.csv,
        output_db=args.output_db,
        table_name=args.table_name,
        model_path=args.model_path,
        variations_per_fact=args.variations_per_fact,
        max_facts=args.max_facts,
        use_mock_llm=args.mock_llm,
        threads=args.threads,
        verify_query=args.query
    )


if __name__ == "__main__":
    main()
