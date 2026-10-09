"""Memory & VRAM profiling script testing 100 consecutive generations for leaks."""

import gc
import os
import sys
import time
from typing import Any, Dict, List, Optional
import psutil

# Ensure core and tests are on path
bench_dir = os.path.dirname(os.path.abspath(__file__))
core_dir = os.path.abspath(os.path.join(bench_dir, "..", "..", "core"))
for p in [bench_dir, core_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)


def get_current_memory_mb() -> Dict[str, float]:
    """Capture current process RSS, VMS, and VRAM (if CUDA available)."""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    rss_mb = mem_info.rss / (1024 * 1024)
    vms_mb = mem_info.vms / (1024 * 1024)

    vram_allocated_mb = 0.0
    vram_reserved_mb = 0.0
    try:
        import torch
        if torch.cuda.is_available():
            vram_allocated_mb = torch.cuda.memory_allocated() / (1024 * 1024)
            vram_reserved_mb = torch.cuda.memory_reserved() / (1024 * 1024)
    except Exception:
        pass

    return {
        "rss_mb": round(rss_mb, 2),
        "vms_mb": round(vms_mb, 2),
        "vram_allocated_mb": round(vram_allocated_mb, 2),
        "vram_reserved_mb": round(vram_reserved_mb, 2)
    }


def run_memory_leak_benchmark(
    iterations: int = 100,
    model_path: Optional[str] = None,
    mock_llm: bool = False
) -> Dict[str, Any]:
    """Execute consecutive LLM generations while profiling RSS and VRAM."""
    print("=" * 65)
    print(f"      MEMORY & VRAM LEAK PROFILING ({iterations} GENERATIONS)")
    print("=" * 65)

    llm = None
    if not mock_llm:
        default_model = os.path.join(core_dir, "models", "AstroSage-8B-BF16.gguf")
        target_model = model_path or default_model
        if os.path.exists(target_model):
            print(f"[MemoryProfiler] Loading model '{target_model}'...")
            from llama_cpp import Llama
            llm = Llama(
                model_path=target_model,
                n_threads=12,
                n_ctx=256,
                verbose=False
            )
        else:
            print(f"[MemoryProfiler] Model not found at '{target_model}'. Using mock generator.")
            mock_llm = True
    else:
        print("[MemoryProfiler] Running in mock generation mode.")

    prompt = "Q: What is a star? A:"

    # Warmup iteration to load runtime buffers and modules
    if llm:
        _ = llm(prompt, max_tokens=2, stop=["\n"])
    else:
        _ = [float(x) for x in range(1000)]
        get_current_memory_mb()

    gc.collect()
    time.sleep(0.2)

    initial_mem = get_current_memory_mb()
    print(f"[Baseline Memory] RSS: {initial_mem['rss_mb']} MB | VRAM: {initial_mem['vram_allocated_mb']} MB")

    snapshots: List[Dict[str, Any]] = []
    sample_interval = max(1, iterations // 10)

    peak_rss = initial_mem["rss_mb"]
    peak_vram = initial_mem["vram_allocated_mb"]

    t0 = time.time()
    for i in range(1, iterations + 1):
        if llm:
            _ = llm(prompt, max_tokens=1, stop=["\n"])
        else:
            # Synthetic allocation/free simulation
            _ = [float(x) for x in range(1000)]

        # Periodic memory sampling
        if i == 1 or i % sample_interval == 0 or i == iterations:
            mem = get_current_memory_mb()
            peak_rss = max(peak_rss, mem["rss_mb"])
            peak_vram = max(peak_vram, mem["vram_allocated_mb"])
            snapshots.append({
                "iteration": i,
                "rss_mb": mem["rss_mb"],
                "vram_allocated_mb": mem["vram_allocated_mb"]
            })
            print(f"  Iteration {i:3d}/{iterations} | RSS: {mem['rss_mb']:7.2f} MB | VRAM: {mem['vram_allocated_mb']:6.2f} MB", flush=True)

    gc.collect()
    time.sleep(0.5)
    final_mem = get_current_memory_mb()
    elapsed = time.time() - t0

    rss_drift = round(final_mem["rss_mb"] - initial_mem["rss_mb"], 2)
    vram_drift = round(final_mem["vram_allocated_mb"] - initial_mem["vram_allocated_mb"], 2)

    # Calculate average drift per iteration
    rss_drift_per_iter = round(rss_drift / max(1, iterations), 4)

    # A leak is detected if memory continuously drifts upward by more than 50MB
    leak_detected = rss_drift > 50.0 or vram_drift > 20.0

    print("\n" + "=" * 65)
    print(f"MEMORY PROFILING COMPLETE ({elapsed:.2f}s)")
    print(f"Initial RSS: {initial_mem['rss_mb']} MB  -->  Final RSS: {final_mem['rss_mb']} MB  (Drift: {rss_drift:+.2f} MB)")
    print(f"Peak RSS:    {peak_rss} MB")
    print(f"Drift Rate:  {rss_drift_per_iter} MB/iteration")
    print(f"VRAM Drift:  {vram_drift:+.2f} MB (Peak: {peak_vram} MB)")
    print(f"Status:      {'PASS (NO LEAK DETECTED)' if not leak_detected else 'FAIL (POTENTIAL LEAK)'}")
    print("=" * 65)

    return {
        "iterations": iterations,
        "elapsed_seconds": round(elapsed, 2),
        "initial_rss_mb": initial_mem["rss_mb"],
        "final_rss_mb": final_mem["rss_mb"],
        "peak_rss_mb": peak_rss,
        "rss_drift_mb": rss_drift,
        "rss_drift_per_iter_mb": rss_drift_per_iter,
        "initial_vram_mb": initial_mem["vram_allocated_mb"],
        "final_vram_mb": final_mem["vram_allocated_mb"],
        "vram_drift_mb": vram_drift,
        "leak_detected": leak_detected,
        "snapshots": snapshots
    }


def test_memory_profiling_logic():
    """Unit test for memory leak profiling logic using synthetic workload."""
    results = run_memory_leak_benchmark(iterations=10, mock_llm=True)
    assert results["iterations"] == 10
    assert results["leak_detected"] is False
    assert len(results["snapshots"]) >= 2


if __name__ == "__main__":
    run_memory_leak_benchmark(iterations=100)
