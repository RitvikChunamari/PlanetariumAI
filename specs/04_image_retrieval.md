# Specification 04: Authoritative Image Retrieval

## 1. Objective
Enable the system to understand "show me" visual intents, fetch high-quality astronomical imagery from authoritative sources (like NASA), cache them locally for offline use, and display them in the React UI alongside the synthesized speech.

## 2. Architecture & Flow
1. **Intent Detection:** AstroSage-8B is prompted to recognize when a user requests a visual (e.g., "show me," "what does X look like"). It will output a structured JSON tool call (e.g., `{"action": "fetch_image", "query": "Orion Nebula"}`) alongside its spoken response.
2. **The Fetcher Module:** The Python backend intercepts this tool call and queries the NASA Image and Video Library API (`images-api.nasa.gov`). 
3. **Local Caching (Offline Mode Prep):** Downloaded images and their metadata (Title, Source, Date, Description) are saved to a local `/cache/images` directory so identical future queries do not require internet access.
4. **WebSocket Transport:** The server sends a JSON control message to the React frontend containing the local image URI and metadata *before* the TTS audio begins playing.
5. **Swiss Design UI:** The React frontend displays the image with a strict typographic hierarchy (Image on the left/top, clear captions, stark metadata presentation) avoiding unnecessary animations or clutter.

## 3. Technology Stack
- **Backend Image Fetching:** Python `requests`, caching to local filesystem.
- **API Source:** NASA Image API (Free, no API key required for basic rate limits).
- **LLM Tool Calling:** `llama-cpp-python` grammar constraints or system prompt JSON formatting to force AstroSage-8B to output a reliable image query.
- **Frontend Display:** React components styled with Tailwind CSS, utilizing CSS Grid for a museum-plaque aesthetic.

## 4. Implementation Steps
1. Create an `images/` module in the Python backend to handle querying the NASA API, downloading the image, and saving metadata.
2. Update the AstroSage-8B system prompt to instruct the model to output a `<TOOL:fetch_image>Search Term</TOOL>` token when a visual is requested.
3. Modify the orchestrator to parse the LLM stream, intercept the tool token, fetch the image, and send it via WebSocket.
4. Build a new React component (`<AstroMediaViewer />`) that dynamically appears when an image payload is received over the WebSocket.