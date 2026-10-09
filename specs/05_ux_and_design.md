# Specification 05: Swiss Design UI & Audio Interaction Overhaul

## 1. Objective
Refactor the React PWA frontend to adhere strictly to the Swiss International Typographic Style. The interface must be legible from a distance, highly accessible (WCAG 2.2 / ADA Kiosk guidelines), and operate seamlessly with natural voice interactions, including real-time user barge-in.

## 2. Visual Design System (Swiss Style)
- **Typography:** Use a clean, neo-grotesque sans-serif font (e.g., Inter, Roboto, or a local Helvetica Neue equivalent). Use strict, mathematical size scales (e.g., 8pt baseline grid).
- **Layout & Grid:** Implement a rigid CSS Grid (12-column layout). The UI must be asymmetric but perfectly aligned, utilizing massive amounts of intentional whitespace.
- **Color Palette:** High-contrast, constrained palette. 
  - Background: Off-black (`#111111`) to match the dark environment of a planetarium.
  - Typography: Pure White (`#FFFFFF`) or stark Off-White (`#F5F5F5`).
  - Accents: Use a single, vibrant accent color (e.g., "International Orange" or "NASA Red") sparingly, only for active states (e.g., when the microphone is listening).
- **Decorations:** No glassmorphism, no drop shadows, no gradients, and no rounded corners on primary structural elements. Focus entirely on information hierarchy.

## 3. Accessibility & Kiosk Mandates
- **Contrast:** Ensure a minimum 70% contrast ratio for all text. 
- **Touch Targets:** Any interactive UI elements (e.g., "Stop AI", "Show Options") must be massive (minimum 48x48px, ideally larger for kiosk touchscreen compliance).
- **State Transparency:** The UI must display the AI's exact state in massive typography: `[ LISTENING ]`, `[ PROCESSING ]`, `[ SPEAKING ]`, `[ RETRIEVING ARCHIVES ]`.
- **Text Readability:** Limit line lengths to 60-70 characters. The live transcription must type out clearly in a large font to support deaf/hard-of-hearing users.

## 4. Audio Interaction & "Barge-In" UX
The user must be able to interrupt the AI while it is speaking without touching the screen.
1. **Continuous Mic Stream:** The Web Audio API capture remains active even while Kokoro TTS audio is playing.
2. **Local Echo Cancellation:** If hardware Acoustic Echo Cancellation (AEC) is insufficient, implement a basic programmatic gate: if Silero VAD detects speech *significantly louder* than the baseline TTS output, flag it as a user interrupt.
3. **Interrupt Event:** When the React UI detects an interrupt, it immediately stops the active HTML5 Audio playback queue and sends an `{"event": "interrupt"}` JSON message to the WebSocket.
4. **Backend Flush:** Upon receiving the interrupt, the Python server immediately terminates the active `llama.cpp` generation and drops all pending Kokoro TTS tasks, clearing the way for the new prompt.

## 5. Implementation Steps
1. **Tailwind Config:** Rewrite `tailwind.config.js` to enforce the custom spacing scale (8pt grid), the restricted color palette, and the neo-grotesque font family.
2. **Component Refactor:** Rebuild the main chat/display interface into distinct, grid-aligned panels:
   - *Left/Top Panel:* The massive active state indicator and live user transcription.
   - *Right/Bottom Panel:* The AI's response text and the `<AstroMediaViewer />` (from Phase 4).
3. **Audio Refactor:** Update the audio hook in React to support a `stop()` method that instantly flushes the playback queue and sends the interrupt signal.
4. **Backend Interrupt Handler:** Add a listener in the FastAPI WebSocket loop to catch the interrupt signal and gracefully cancel the active asyncio generation tasks.