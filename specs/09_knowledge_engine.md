# Specification 09: Planetarium Knowledge Engine Pipeline

## 1. Objective
Build an automated, local, LLM-assisted data pipeline to curate, fact-check, deduplicate, and ingest 100,000 astronomical questions and answers into the LanceDB vector database. This script runs independently of the main server to build the production database.

## 2. Technology Stack
- **Data Orchestration:** Python (Pandas/Polars for fast tabular processing).
- **Generator/Verifier Model:** `DeepSeek-R1-Distill-Llama-8B` (Utilized for its extreme reasoning and fact-checking capabilities, swapped in temporarily just for the pipeline).
- **Embedding:** `Nomic-Embed-Text-v1.5`.
- **Database:** `LanceDB`.

## 3. The 4-Step Pipeline Architecture
1. **Seed Ingestion:** Parse raw CSVs of public planetarium FAQs, NASA mission fact sheets, and open astronomy datasets.
2. **Synthetic Expansion:** For every seed fact (e.g., "Jupiter has 95 moons"), prompt the reasoning LLM to generate 10 conversational question variations mapped to that intent (e.g., "How many moons does Jupiter have?", "Does Jupiter have more moons than Saturn?").
3. **Fact-Checking (LLM-as-a-Judge):** Pass the generated QA pairs back through the reasoning model with a strict system prompt: *"Are there any factual inaccuracies in this answer based on current consensus? Reply PASS or FAIL."* Any `FAIL` is automatically discarded.
4. **Vectorization & Storage:** The approved QA pairs are embedded via Nomic and written to LanceDB with required metadata fields:
   - `intent_category` (e.g., Solar System, Cosmology)
   - `question_text`
   - `answer_text`
   - `citation_source` (e.g., NASA JPL)

## 4. Implementation Steps
1. Create a `tools/data_pipeline/` directory outside the main app.
2. Write a Python script (`build_db.py`) utilizing `llama-cpp-python` to load the reasoning model.
3. Implement the `SyntheticExpander` class to generate question variations.
4. Implement the `FactChecker` class to validate the outputs.
5. Create a batch processing loop that processes a sample CSV of 1,000 seed facts, embeds them, and outputs a production-ready LanceDB `.lance` dataset that the main Tauri app can mount on boot.