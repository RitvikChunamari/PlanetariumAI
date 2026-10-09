import sys
import os
import platform
import argparse
import shutil
import PyInstaller.__main__

def get_default_target_triple():
    machine = platform.machine().lower()
    system = platform.system().lower()
    
    if system == "windows":
        return "x86_64-pc-windows-msvc"
    elif system == "darwin":
        if "arm" in machine or "aarch64" in machine:
            return "aarch64-apple-darwin"
        else:
            return "x86_64-apple-darwin"
    elif system == "linux":
        if "arm" in machine or "aarch64" in machine:
            return "aarch64-unknown-linux-gnu"
        else:
            return "x86_64-unknown-linux-gnu"
    return "x86_64-unknown-linux-gnu"

def build(target_triple=None, onefile=True):
    target = target_triple or get_default_target_triple()
    is_windows = "windows" in target
    ext = ".exe" if is_windows else ""
    
    binary_name = f"planetarium-ai-server-{target}"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, "main.py")
    
    tauri_binaries_dir = os.path.abspath(os.path.join(script_dir, "..", "app", "src-tauri", "binaries"))
    os.makedirs(tauri_binaries_dir, exist_ok=True)
    
    dist_dir = os.path.join(script_dir, "dist")
    build_dir = os.path.join(script_dir, "build")
    
    print(f"======================================================================")
    print(f"  PLANETARIUMAI - PYINSTALLER BACKEND FREEZER")
    print(f"======================================================================")
    print(f"  Target Architecture : {target}")
    print(f"  Binary Name         : {binary_name}{ext}")
    print(f"  Output Directory    : {tauri_binaries_dir}")
    print(f"  Packaging Mode      : {'Single Executable (--onefile)' if onefile else 'Directory (--onedir)'}")
    print(f"======================================================================\n")

    pyinstaller_args = [
        main_script,
        '--name', binary_name,
        '--onefile' if onefile else '--onedir',
        '--distpath', tauri_binaries_dir,
        '--workpath', build_dir,
        '--specpath', script_dir,
        # Hidden imports for Uvicorn and FastAPI ASGI server
        '--hidden-import', 'uvicorn.logging',
        '--hidden-import', 'uvicorn.loops',
        '--hidden-import', 'uvicorn.loops.auto',
        '--hidden-import', 'uvicorn.protocols',
        '--hidden-import', 'uvicorn.protocols.http',
        '--hidden-import', 'uvicorn.protocols.http.auto',
        '--hidden-import', 'uvicorn.protocols.websockets',
        '--hidden-import', 'uvicorn.protocols.websockets.auto',
        '--hidden-import', 'uvicorn.lifespan',
        '--hidden-import', 'uvicorn.lifespan.on',
        '--hidden-import', 'fastapi',
        '--hidden-import', 'starlette',
        '--hidden-import', 'websockets',
        # Collect dynamic native libraries and dependencies
        '--collect-all', 'llama_cpp',
        '--collect-all', 'faster_whisper',
        '--collect-all', 'ctranslate2',
        '--collect-all', 'kokoro_onnx',
        '--collect-all', 'onnxruntime',
        '--collect-all', 'lancedb',
        '--collect-all', 'sentence_transformers',
        '--noconfirm',
        '--clean'
    ]

    print(f"Executing PyInstaller with {len(pyinstaller_args)} arguments...")
    PyInstaller.__main__.run(pyinstaller_args)
    
    expected_output = os.path.join(tauri_binaries_dir, f"{binary_name}{ext}")
    if os.path.exists(expected_output):
        size_mb = os.path.getsize(expected_output) / (1024 * 1024)
        print(f"\n[Success] Standalone Sidecar Binary generated:")
        print(f"  -> Path: {expected_output}")
        print(f"  -> Size: {size_mb:.2f} MB")
        return expected_output
    else:
        print(f"\n[Warning] Expected binary not found at {expected_output}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Freeze PlanetariumAI Python Backend with PyInstaller")
    parser.add_argument("--target", default=None, help="Target triple (e.g. x86_64-pc-windows-msvc, aarch64-apple-darwin)")
    parser.add_argument("--onedir", action="store_true", help="Build as directory instead of single file")
    args = parser.parse_args()
    
    build(target_triple=args.target, onefile=not args.onedir)
