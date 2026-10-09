# Specification 03: Planetarium Knowledge Base (RAG)

## 1. Objective
Integrate a local vector database to ground AstroSage-8B's responses in curated astronomical data. This prevents hallucinations and ensures the assistant can answer specific, obscure, or highly technical questions accurately without relying on cloud APIs.

## 2. Technology Stack
- **Vector Database:** `lancedb` (embedded, runs directly on disk/memory with zero configuration, highly optimized for local Python environments).
- **Embedding Model:** `nomic-ai/nomic-embed-text-v1.5` (via ONNX or `llama.cpp`) – chosen for its highly efficient footprint and 8192-token context length.
- **Data Source:** A local JSON/CSV file serving as the seed for our 100k curated planetarium QA dataset.

## 3. Architecture & Routing
1. **Intent Routing:** Before passing transcribed text to the main LLM, the orchestrator determines if the query is a factual question (requiring database retrieval) or casual conversational interaction.
2. **Embedding:** The user's transcribed question is converted into a vector using the Nomic embedding model.
3. **Retrieval:** LanceDB performs a similarity search to retrieve the top 3 most relevant factual snippets.
4. **Augmented Generation:** The retrieved facts are injected into the AstroSage-8B system prompt.
5. **Output Streaming:** The LLM generates the final answer based *only* on the retrieved context, streaming the response directly into the Kokoro TTS engine as built in Phase 2.

## 4. Implementation Steps
1. Create a `rag/` module in the Python backend.
2. Initialize a LanceDB table and write a standalone Python script to ingest a mock dataset (e.g., 20 sample planetarium facts and mission details) to test the embeddings.
3. Load the `nomic-embed-text` model into memory on server startup alongside the other models.
4. Modify the Phase 2 WebSocket inference loop: `User Speech -> Whisper -> RAG Search -> AstroSage-8B -> Kokoro TTS`.
5. Update the React frontend to display a new visual state (e.g., "Searching Archives...") when the RAG pipeline is triggered, maintaining the Swiss Design typography.