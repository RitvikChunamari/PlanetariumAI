import os
import httpx
import urllib.request
from huggingface_hub import hf_hub_download

os.makedirs("models", exist_ok=True)

# 1. AstroSage
repo_id = "AstroMLab/AstroSage-8B-GGUF"
with httpx.Client() as client:
    response = client.get(f"https://huggingface.co/api/models/{repo_id}/tree/main")
    files_info = response.json()

gguf_files = [f["path"] for f in files_info if f["path"].endswith(".gguf")]
print("Found GGUF files:", gguf_files)

target_file = None
for f in gguf_files:
    if "Q4_K_M" in f:
        target_file = f
        break
if not target_file and gguf_files:
    target_file = gguf_files[0]

if target_file:
    print(f"Downloading {target_file} from {repo_id}...")
    hf_hub_download(repo_id=repo_id, filename=target_file, local_dir="models")

# 2. Kokoro
print("Downloading Kokoro ONNX...")
urllib.request.urlretrieve("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx", "models/kokoro-v1.0.onnx")
urllib.request.urlretrieve("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin", "models/voices-v1.0.bin")

print("All downloads complete.")
