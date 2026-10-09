#!/usr/bin/env python3
"""
PlanetariumAI - Universal Desktop Application Packaging Engine
Coordinates PyInstaller backend freezing, resource staging (LanceDB & Models),
and Tauri v2 cross-platform compilation for macOS, Windows, and Linux.
"""

import os
import sys
import platform
import argparse
import subprocess
import shutil

def get_target_triple():
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
    return "x86_64-pc-windows-msvc"

def run_command(cmd, cwd=None, env=None):
    print(f"\n[EXEC] {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    
    # Ensure Cargo/Rust is in PATH on Windows if installed in ~/.cargo/bin
    user_cargo_bin = os.path.expanduser("~/.cargo/bin")
    if os.path.exists(user_cargo_bin) and user_cargo_bin not in run_env.get("PATH", ""):
        run_env["PATH"] = f"{user_cargo_bin};{run_env.get('PATH', '')}"

    res = subprocess.run(cmd, cwd=cwd, env=run_env, shell=isinstance(cmd, str))
    if res.returncode != 0:
        print(f"[ERROR] Command failed with exit code {res.returncode}")
        return False
    return True

def package(target_override=None, skip_backend=False, skip_frontend=False):
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    app_dir = os.path.join(root_dir, "app")
    core_dir = os.path.join(root_dir, "core")
    target = target_override or get_target_triple()
    is_windows = "windows" in target
    binary_ext = ".exe" if is_windows else ""
    
    sidecar_name = f"planetarium-ai-server-{target}{binary_ext}"
    sidecar_path = os.path.join(app_dir, "src-tauri", "binaries", sidecar_name)

    print("======================================================================")
    print("      PLANETARIUMAI - DESKTOP PACKAGING ENGINE (TAURI v2)")
    print("======================================================================")
    print(f"  Root Directory      : {root_dir}")
    print(f"  Target Architecture : {target}")
    print(f"  Sidecar Binary      : {sidecar_path}")
    print("======================================================================\n")

    # 1. Freeze Python backend with PyInstaller if needed
    if not skip_backend:
        print(">>> Step 1: Freezing Python backend with PyInstaller...")
        python_exe = sys.executable
        venv_python = os.path.join(core_dir, ".venv", "Scripts" if is_windows else "bin", f"python{binary_ext}")
        if os.path.exists(venv_python):
            python_exe = venv_python
            
        build_script = os.path.join(core_dir, "build_backend.py")
        if not run_command([python_exe, build_script, "--target", target], cwd=core_dir):
            print("[ERROR] Failed to freeze Python backend.")
            return False
    else:
        print(">>> Step 1: Skipping backend freeze (using existing binary)...")

    if not os.path.exists(sidecar_path):
        print(f"[ERROR] Sidecar binary not found at {sidecar_path}")
        return False

    # 2. Stage Resources (LanceDB, Models, Assets)
    print("\n>>> Step 2: Staging resources for installer bundle...")
    resources_dir = os.path.join(app_dir, "src-tauri", "resources")
    os.makedirs(resources_dir, exist_ok=True)
    
    # Stage LanceDB
    lancedb_src = os.path.join(core_dir, "data", "lancedb")
    lancedb_dst = os.path.join(resources_dir, "data", "lancedb")
    if os.path.exists(lancedb_src):
        os.makedirs(os.path.dirname(lancedb_dst), exist_ok=True)
        if not os.path.exists(lancedb_dst):
            print(f"  -> Copying LanceDB vectors to {lancedb_dst}")
            shutil.copytree(lancedb_src, lancedb_dst, dirs_exist_ok=True)
            
    # Stage lightweight models
    models_src = os.path.join(core_dir, "models")
    models_dst = os.path.join(resources_dir, "models")
    os.makedirs(models_dst, exist_ok=True)
    if os.path.exists(models_src):
        for item in ["kokoro-v1.0.onnx", "voices-v1.0.bin", "whisper-dysarthria-ct2"]:
            s = os.path.join(models_src, item)
            d = os.path.join(models_dst, item)
            if os.path.exists(s) and not os.path.exists(d):
                print(f"  -> Staging model component: {item}")
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)

    # 3. Build Frontend with Vite
    if not skip_frontend:
        print("\n>>> Step 3: Compiling React PWA frontend with Vite...")
        pnpm_cmd = "pnpm.cmd" if is_windows else "pnpm"
        if not run_command([pnpm_cmd, "run", "build"], cwd=app_dir):
            print("[ERROR] Failed to compile React frontend.")
            return False

    # 4. Build Tauri Desktop Installer
    print("\n>>> Step 4: Compiling Tauri v2 Desktop Installer...")
    pnpm_cmd = "pnpm.cmd" if is_windows else "pnpm"
    tauri_build_cmd = [pnpm_cmd, "tauri", "build"]
    if target_override:
        tauri_build_cmd.extend(["--target", target_override])
    if not run_command(tauri_build_cmd, cwd=app_dir):
        print("[ERROR] Failed to build Tauri installer.")
        return False

    # 5. Report Generated Installers
    print("\n======================================================================")
    print("  INSTALLER BUILD COMPLETE - BUNDLE ARTIFACTS")
    print("======================================================================")
    bundle_dir = os.path.join(app_dir, "src-tauri", "target", "release", "bundle")
    if os.path.exists(bundle_dir):
        for root, _, files in os.walk(bundle_dir):
            for f in files:
                f_path = os.path.join(root, f)
                f_size_mb = os.path.getsize(f_path) / (1024 * 1024)
                print(f"  [Artifact] {f} ({f_size_mb:.2f} MB)")
                print(f"             Path: {f_path}")
    print("======================================================================\n")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package PlanetariumAI Desktop Application")
    parser.add_argument("--target", default=None, help="Target architecture (e.g. x86_64-pc-windows-msvc, aarch64-apple-darwin, x86_64-unknown-linux-gnu)")
    parser.add_argument("--skip-backend", action="store_true", help="Skip PyInstaller freeze")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip Vite build")
    args = parser.parse_args()

    success = package(target_override=args.target, skip_backend=args.skip_backend, skip_frontend=args.skip_frontend)
    sys.exit(0 if success else 1)
