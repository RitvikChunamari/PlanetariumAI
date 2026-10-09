import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import json
import glob
import os
import queue
import threading
import sys
import re
import uuid

from vad import SileroVAD
from inference.asr import WhisperASR
from inference.llm import AstroSageLLM
from inference.tts import KokoroTTS
from rag.database import KnowledgeBase
from images.fetcher import NasaImageFetcher

app = FastAPI(title="PlanetariumAI")

os.makedirs("cache/images", exist_ok=True)
app.mount("/images", StaticFiles(directory="cache/images"), name="images")

# Mount React frontend static assets if dist exists
dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "dist"))
if os.path.exists(os.path.join(dist_dir, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_resource_path(relative_path: str) -> str:
    """
    Locates assets and model files seamlessly across development,
    PyInstaller frozen execution, and Tauri packaged applications.
    """
    env_override = os.environ.get(f"PLANETARIUM_{relative_path.upper()}_DIR")
    if env_override and os.path.exists(env_override):
        return env_override

    base_dir = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidates = [
            os.path.join(exe_dir, relative_path),
            os.path.join(exe_dir, "resources", relative_path),
            os.path.join(exe_dir, "..", "Resources", relative_path),
            os.path.join(getattr(sys, '_MEIPASS', ''), relative_path),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
    p = os.path.join(base_dir, relative_path)
    if os.path.exists(p):
        return p
    return relative_path

def get_astrosage_path():
    models_dir = get_resource_path("models")
    files = glob.glob(os.path.join(models_dir, "*.gguf"))
    if files:
        return files[0]
    return os.path.join(models_dir, "astrosage-8b.gguf")
from audio_processing import NoiseFilter
from inference.asr import WhisperASR
from tts_normalizer.normalizer import TextNormalizer

class Pipeline:
    def __init__(self):
        print("Loading Noise Filter...", flush=True)
        self.noise_filter = NoiseFilter()
        print("Loading VAD...", flush=True)
        self.vad = SileroVAD()
        print("Loading ASR...", flush=True)
        self.asr = WhisperASR()
        print("Loading RAG Database...", flush=True)
        self.kb = KnowledgeBase()
        print("Loading Image Fetcher...", flush=True)
        self.fetcher = NasaImageFetcher()
        print("Loading LLM...", flush=True)
        self.llm = AstroSageLLM(get_astrosage_path())
        print("Loading Normalizer...", flush=True)
        self.normalizer = TextNormalizer()
        print("Loading TTS...", flush=True)
        self.tts = KokoroTTS()
        # Quick non-blocking TTS warmup
        try:
            _ = self.tts.synthesize("Cosmos")
        except Exception:
            pass

pipeline = None

@app.on_event("startup")
def startup_event():
    global pipeline
    try:
        pipeline = Pipeline()
        print("Pipeline fully loaded.", flush=True)
    except Exception as e:
        print(f"Error loading pipeline: {e}", flush=True)

@app.websocket("/ws/audio")
async def audio_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected to audio endpoint", flush=True)
    
    await websocket.send_text(json.dumps({"type": "state", "state": "Listening..."}))
    
    audio_buffer = bytearray()
    silence_threshold = 12  # ~1.5s natural pause tolerance (accommodates dysarthric speech patterns with zero lag)
    silence_frames = 0
    is_speaking = False
    
    current_interrupt_event = None
    current_sender_task = None
    
    async def process_user_query(text: str, query_id: str = None, is_voice: bool = False):
        nonlocal current_interrupt_event, current_sender_task
        
        # Interrupt any active speech/inference before processing new turn
        if current_interrupt_event:
            current_interrupt_event.set()
        if current_sender_task and not current_sender_task.done():
            current_sender_task.cancel()
                
        loop = asyncio.get_running_loop()
        turn_id = query_id or f"turn-{uuid.uuid4().hex[:8]}"
        
        print(f"User Query [{turn_id}]: {text}", flush=True)
        # 1. Send single authoritative user message (frontend deduplicates by turn_id)
        await websocket.send_text(json.dumps({
            "type": "user_message",
            "turn_id": turn_id,
            "text": text,
            "is_voice": is_voice
        }))
        
        # Guard: check if pipeline is ready
        if pipeline is None:
            await websocket.send_text(json.dumps({
                "type": "state",
                "turn_id": turn_id,
                "state": "Listening..."
            }))
            return

        # 2. Instant Semantic Cache check (<10ms latency for frequent cosmology questions / memory)
        instant_answer = await loop.run_in_executor(None, pipeline.kb.get_instant_match, text)
        if instant_answer:
            print(f"[Core] Instant Cache Hit! (<10ms) Answering: {instant_answer[:45]}...", flush=True)
            norm_answer = pipeline.normalizer.clean(instant_answer)
            
            await websocket.send_text(json.dumps({
                "type": "state",
                "turn_id": turn_id,
                "state": "Speaking..."
            }))
            
            await websocket.send_text(json.dumps({
                "type": "assistant_chunk",
                "turn_id": turn_id,
                "text": norm_answer
            }))
            
            # Synthesize audio chunk immediately
            audio_chunk = await loop.run_in_executor(None, pipeline.tts.synthesize, norm_answer)
            if audio_chunk:
                await websocket.send_bytes(audio_chunk)
                
            # Persist learned turn in conversation memory
            pipeline.kb.memory.save_turn(text, norm_answer, turn_id=turn_id)
            
            await websocket.send_text(json.dumps({
                "type": "turn_complete",
                "turn_id": turn_id,
                "state": "Listening..."
            }))
            return

        # 3. Fallback to RAG search and streaming LLM inference
        print("Searching RAG archives...", flush=True)
        facts = await loop.run_in_executor(None, pipeline.kb.search, text)
        
        if facts:
            context = "\n".join([f"- {fact}" for fact in facts])
            llm_prompt = (
                f"Astronomical archives:\n{context}\n\n"
                f"User request: {text}\n\n"
                f"Answer concisely. If the user asks to see or show an image of an object, "
                f"begin your response with <TOOL:fetch_image>object_name</TOOL>."
            )
            print("Facts found:", facts, flush=True)
        else:
            llm_prompt = text
            
        await websocket.send_text(json.dumps({
            "type": "state",
            "turn_id": turn_id,
            "state": "Speaking..."
        }))
        
        print("Generating response...", flush=True)
        q = asyncio.Queue()
        interrupt_event = threading.Event()
        current_interrupt_event = interrupt_event
        accumulated_chunks = []
        
        def generate_and_synthesize(prompt_text, ev, out_q):
            tool_pattern = re.compile(r'<TOOL:fetch_image>(.*?)</TOOL>')
            try:
                for sentence in pipeline.llm.sentence_chunker(prompt_text, ev=ev):
                    if ev.is_set():
                        break
                        
                    match = tool_pattern.search(sentence)
                    if match:
                        search_term = match.group(1).strip()
                        sentence = tool_pattern.sub("", sentence).strip()
                        print(f"Tool Call Intercepted: fetch_image({search_term})", flush=True)
                        img_data = pipeline.fetcher.fetch_image(search_term)
                        if img_data:
                            loop.call_soon_threadsafe(out_q.put_nowait, {"type": "image", "data": img_data})
                        if not sentence:
                            sentence = f"Here is an image of {search_term} from the NASA archives."
                            
                    if sentence:
                        sentence = pipeline.normalizer.clean(sentence)
                        accumulated_chunks.append(sentence)
                        print(f"Synthesizing: {sentence}", flush=True)
                        # Stream text chunk to messaging UI immediately
                        loop.call_soon_threadsafe(out_q.put_nowait, {"type": "text", "data": sentence})
                        audio_chunk = pipeline.tts.synthesize(sentence)
                        if ev.is_set():
                            break
                        if audio_chunk:
                            loop.call_soon_threadsafe(out_q.put_nowait, {"type": "audio", "data": audio_chunk})
            except Exception as e:
                print(f"Generation error: {e}", flush=True)
            loop.call_soon_threadsafe(out_q.put_nowait, None)
            
        gen_thread = threading.Thread(target=generate_and_synthesize, args=(llm_prompt, interrupt_event, q), daemon=True)
        gen_thread.start()
        
        async def send_queue(ev, out_q, t_id):
            try:
                while True:
                    item = await out_q.get()
                    if item is None or ev.is_set():
                        break
                    if item["type"] == "text":
                        await websocket.send_text(json.dumps({
                            "type": "assistant_chunk",
                            "turn_id": t_id,
                            "text": item["data"]
                        }))
                    elif item["type"] == "audio":
                        await websocket.send_bytes(item["data"])
                    elif item["type"] == "image":
                        await websocket.send_text(json.dumps({
                            "type": "image",
                            "turn_id": t_id,
                            "image": item["data"]
                        }))
                
                # Turn finished cleanly
                if not ev.is_set():
                    full_answer = " ".join(accumulated_chunks)
                    if full_answer:
                        pipeline.kb.memory.save_turn(text, full_answer, turn_id=t_id)
                        
                    await websocket.send_text(json.dumps({
                        "type": "turn_complete",
                        "turn_id": t_id,
                        "state": "Listening..."
                    }))
                print("Finished sending response turn", flush=True)
            except Exception as e:
                print(f"send_queue connection closed: {e}", flush=True)
            
        current_sender_task = asyncio.create_task(send_queue(interrupt_event, q, turn_id))

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            
            if "bytes" in message:
                data = message["bytes"]
                if pipeline is None:
                    continue
                    
                # Ultra-fast VAD gating (<0.5ms) on raw 16kHz audio with dysarthria-sensitive acoustic threshold
                is_speech = pipeline.vad.is_speech(data, threshold=0.28)
                
                if is_speech:
                    if not is_speaking:
                        if current_sender_task and not current_sender_task.done():
                            print("Barge-in detected via VAD!", flush=True)
                            if current_interrupt_event:
                                current_interrupt_event.set()
                            await websocket.send_text(json.dumps({
                                "type": "state",
                                "state": "Interrupted"
                            }))
                            
                        is_speaking = True
                        silence_frames = 0
                        audio_buffer.clear()
                    
                    # Store RAW pristine mic audio in buffer for Faster-Whisper
                    audio_buffer.extend(data)
                    silence_frames = 0
                else:
                    if is_speaking:
                        silence_frames += 1
                        # Continue capturing raw buffer during pauses
                        audio_buffer.extend(data)
                        
                        if silence_frames > silence_threshold:
                            is_speaking = False
                            silence_frames = 0
                            
                            await websocket.send_text(json.dumps({
                                "type": "state",
                                "state": "Thinking..."
                            }))
                            
                            print("Transcribing speech (Faster-Whisper int8)...", flush=True)
                            loop = asyncio.get_running_loop()
                            audio_data_copy = bytes(audio_buffer)
                            text = await loop.run_in_executor(None, pipeline.asr.transcribe, audio_data_copy)
                            audio_buffer.clear()
                            
                            if not text.strip():
                                await websocket.send_text(json.dumps({
                                    "type": "state",
                                    "state": "Listening..."
                                }))
                                continue
                                
                            print(f"Transcription: {text}", flush=True)
                            await process_user_query(text, is_voice=True)

            elif "text" in message:
                try:
                    msg_data = json.loads(message["text"])
                    msg_type = msg_data.get("type")
                    
                    if msg_type == "INTERRUPT":
                        if current_sender_task and not current_sender_task.done():
                            if current_interrupt_event:
                                current_interrupt_event.set()
                            print("Frontend requested INTERRUPT!", flush=True)
                            await websocket.send_text(json.dumps({
                                "type": "state",
                                "state": "Interrupted"
                            }))
                    elif msg_type == "CHAT_MESSAGE":
                        user_text = msg_data.get("text", "").strip()
                        msg_id = msg_data.get("id")
                        if user_text:
                            await process_user_query(user_text, query_id=msg_id, is_voice=False)
                    elif msg_type == "CONFIG":
                        if "silence_threshold" in msg_data:
                            silence_threshold = int(msg_data["silence_threshold"])
                            print(f"Updated silence threshold: {silence_threshold}", flush=True)
                except Exception as e:
                    print(f"Text message error: {e}", flush=True)
                
    except WebSocketDisconnect:
        print("\nClient disconnected", flush=True)
    except Exception as e:
        print(f"\nEndpoint Error: {e}", flush=True)
    finally:
        if current_interrupt_event:
            current_interrupt_event.set()
        if current_sender_task and not current_sender_task.done():
            current_sender_task.cancel()

@app.get("/{full_path:path}")
async def serve_spa(full_path: str = ""):
    """Serve compiled React SPA and static assets, with index.html fallback for client-side routing."""
    file_path = os.path.join(dist_dir, full_path)
    if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    index_path = os.path.join(dist_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "PlanetariumAI Backend API Ready. Build frontend with 'pnpm run build' in /app."}
        
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PlanetariumAI Host Server Sidecar")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    args = parser.parse_args()

    print(f"[PLANETARIUM_SERVER_STARTING:{args.port}]", flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")

