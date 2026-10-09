from llama_cpp import Llama
import re
import threading

class AstroSageLLM:
    def __init__(self, model_path: str):
        self.lock = threading.Lock()
        self.llm = Llama(
            model_path=model_path,
            n_threads=12,
            n_gpu_layers=-1, # Offload all to GPU if possible
            n_ctx=2048,
            verbose=False
        )
        
    def generate_stream(self, prompt: str, ev: threading.Event = None):
        system_prompt = (
            "You are PlanetariumAI, a concise and knowledgeable astronomy assistant. "
            "Always answer questions directly and concisely in 1-2 clear sentences. "
            "CRITICAL INSTRUCTION: ONLY if the user explicitly says 'show me' or asks to see an image, respond by starting your message with <TOOL:fetch_image>X</TOOL> where X is the name of the object. "
            "For general questions without an image request, do not use any tools; answer directly in speech."
        )
        formatted_prompt = f"<|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        
        # Ensure thread-safe exclusive access to llama C++ context
        with self.lock:
            if ev and ev.is_set():
                return
            try:
                # Reset previous state if needed
                self.llm.reset()
                response_stream = self.llm(
                    formatted_prompt,
                    max_tokens=128,
                    stream=True,
                    stop=["<|eot_id|>", "<|end_of_text|>", "<|start_header_id|>"]
                )
                
                for chunk in response_stream:
                    if ev and ev.is_set():
                        break
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        text = chunk["choices"][0]["text"]
                        yield text
            except Exception as e:
                print(f"[AstroSageLLM] Generation exception recovered: {e}", flush=True)
                try:
                    self.llm.reset()
                except Exception:
                    pass
                yield "The celestial object you mentioned is an intriguing subject in astrophysics."
                
    def sentence_chunker(self, prompt: str, ev: threading.Event = None):
        """
        Yields complete sentences or natural speech clauses as they are generated.
        """
        buffer = ""
        sentence_pattern = re.compile(r'([.!?]+(?:\s+|$))')
        clause_pattern = re.compile(r'([,;:\n]+(?:\s+|$))')
        
        for text in self.generate_stream(prompt, ev=ev):
            if ev and ev.is_set():
                break
            buffer += text
            
            # Sentence end boundary
            s_match = sentence_pattern.search(buffer)
            if s_match:
                end_pos = s_match.end()
                sentence = buffer[:end_pos].strip()
                if sentence:
                    yield sentence
                buffer = buffer[end_pos:]
                continue
                
            # Clause boundary if buffer is sufficiently long (>18 chars) for immediate voice delivery
            if len(buffer) > 18:
                c_match = clause_pattern.search(buffer)
                if c_match:
                    end_pos = c_match.end()
                    clause = buffer[:end_pos].strip()
                    if clause:
                        yield clause
                    buffer = buffer[end_pos:]
                
        if buffer.strip() and not (ev and ev.is_set()):
            yield buffer.strip()
