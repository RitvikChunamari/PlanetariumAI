# Specification 06: Acoustic Pre-Processing & Dysarthria Adaptation

## 1. Objective
Ensure the voice capture pipeline functions flawlessly in a loud, echoing planetarium environment and accurately transcribes dysarthric and atypical speech without degradation. 

## 2. Technology Stack
- **Noise Suppression:** `DeepFilterNet3` (Runs in real-time on CPU, exceptionally good at separating speech from HVAC/crowd noise).
- **Voice Activity Detection:** `Silero VAD v4` (Reconfigured to process the *cleaned* audio rather than the raw mic feed).
- **Dysarthria-Aware ASR:** `Faster-Whisper` running a LoRA or fine-tuned checkpoint trained on dysarthric datasets (e.g., TORGO or UASpeech). 

## 3. Architecture & Signal Flow
1. **Raw Capture:** The React client streams raw Opus audio (filled with background noise) over the WebSocket.
2. **Deep Filtering:** The Python backend decodes the audio and streams it immediately through `DeepFilterNet3`. This neural filter strips out projector hum, echoing dome reverberations, and background chatter, isolating the primary speaker.
3. **VAD Gating:** `Silero VAD` analyzes the *filtered* output. Because the noise floor is now artificially zeroed out by DeepFilterNet3, VAD false-positives (the AI accidentally triggering on a child screaming in the background) are virtually eliminated.
4. **Dysarthric Transcription:** When the VAD closes the buffer, it is passed to the specialized `Faster-Whisper` model. Standard ASR models struggle with dysarthria, but a TORGO/UASpeech-adapted Whisper model utilizes the clean phonemes to accurately reconstruct intent.

## 4. Implementation Steps
1. **Module Creation:** Create an `audio_processing/` module in the Python backend.
2. **Integrate DeepFilterNet3:** Install the `deepfilternet` Python package and wrap it in a streaming buffer class that intercepts incoming WebSocket audio chunks.
3. **Adjust the Pipeline:** Route the output of `DeepFilterNet3` directly into the existing `Silero VAD` instance. 
4. **Whisper Swap:** Modify the `Faster-Whisper` loader to pull a dysarthria-tuned checkpoint (e.g., `aufklarer/whisper-dysarthria` or similar huggingface weights) instead of the default `base.en`. 
5. **Adjust Inference Beam Search:** Increase the beam search size (e.g., `beam_size=10`) in Faster-Whisper to allow the model more flexibility in deciphering atypical speech patterns.