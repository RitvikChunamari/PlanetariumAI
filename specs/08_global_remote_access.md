# Specification 08: Global Remote Access (Web App)

## 1. Objective
Transform the system into a globally accessible Progressive Web App (PWA). The heavy AI inference runs on the Host PC, while the React UI is served to remote devices over the public internet. The connection must use Cloudflare Tunnels to ensure secure HTTPS, ultra-low latency WebSocket routing, and zero router port-forwarding.

## 2. Technology Stack
- **Backend/Frontend Server:** FastAPI (configured to serve the compiled React static files and handle WebSocket connections).
- **Network Tunnel:** Cloudflare Tunnels (`cloudflared`).
- **Security:** Cloudflare Zero Trust (to lock the web app behind an authentication gate so only the owner can access it).

## 3. Architecture & Routing Flow
1. **PWA Compilation:** The Vite/React frontend is built into static files (`/dist`).
2. **FastAPI Static Mount:** The Python backend mounts the `/dist` directory at the root (`/`) route, while keeping the `/asr` and `/tts` WebSockets active.
3. **The Tunnel:** The `cloudflared` daemon runs on the Host PC, securely mapping `localhost:8000` to a public HTTPS domain.
4. **Remote Interaction:** 
   - User opens the domain on their phone.
   - PWA loads instantly (cached by Cloudflare).
   - WebSocket connection is established.
   - Opus-encoded audio streams from the phone, through the Cloudflare edge network, directly into the Host PC's RAM for processing, returning TTS audio in < 800ms.

## 4. Implementation Steps
1. **Remove Tauri:** Delete the `src-tauri` directory and remove Tauri dependencies from the frontend. We are building a pure web app.
2. **Configure FastAPI for Production:** Add `StaticFiles` mounting to the `main.py` FastAPI file so it serves the React `index.html` and assets.
3. **CORS & WebSocket Updates:** Update the FastAPI CORS middleware and WebSocket origins to accept connections from the public domain rather than just `localhost`.
4. **Tunnel Setup Script:** Create a Python utility script `setup_tunnel.py` that downloads the `cloudflared` executable, guides the user through authenticating their Cloudflare account, and binds the local server to their public URL.