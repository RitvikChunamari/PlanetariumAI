import os
import sys
import json
import yaml
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core")))

from core.build_backend import get_default_target_triple
from tools.packaging.package_app import get_target_triple

def test_target_triples():
    """Verify target triple detection returns standard valid Rust triples."""
    host_triple = get_target_triple()
    assert host_triple in [
        "x86_64-pc-windows-msvc",
        "aarch64-apple-darwin",
        "x86_64-apple-darwin",
        "x86_64-unknown-linux-gnu",
        "aarch64-unknown-linux-gnu"
    ]

def test_tauri_config_universal_targets():
    """Verify tauri.conf.json has universal targets for macOS, Windows, and Linux."""
    tauri_conf_path = "app/src-tauri/tauri.conf.json"
    assert os.path.exists(tauri_conf_path), "tauri.conf.json not found"
    
    with open(tauri_conf_path, "r", encoding="utf-8") as f:
        conf = json.load(f)
        
    bundle = conf.get("bundle", {})
    targets = bundle.get("targets", [])
    
    # Check all requested installer formats are targeted ('all' builds all platform targets)
    if targets != "all":
        for expected_target in ["msi", "nsis", "dmg", "appimage", "deb"]:
            assert expected_target in targets, f"Missing bundle target: {expected_target}"
    else:
        assert targets == "all"
        
    # Check external sidecar configuration
    external_bin = bundle.get("externalBin", [])
    assert any("planetarium-ai-server" in bin_name for bin_name in external_bin), "Sidecar binary missing from externalBin"
    
    # Check resource staging configuration
    resources = bundle.get("resources", [])
    assert any("resources" in r for r in resources), "Resources missing from bundle resources"

def test_github_actions_workflow_matrix():
    """Verify CI/CD workflow contains Windows x64 and macOS Apple Silicon targets."""
    workflow_path = ".github/workflows/build-installers.yml"
    assert os.path.exists(workflow_path), "CI/CD workflow file not found"
    
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = yaml.safe_load(f)
        
    jobs = workflow.get("jobs", {})
    build_job = jobs.get("build-installers", {})
    matrix = build_job.get("strategy", {}).get("matrix", {}).get("include", [])
    
    platforms = [m.get("platform") for m in matrix]
    targets = [m.get("target") for m in matrix]
    
    assert "windows" in platforms, "Missing Windows target platform in workflow"
    assert "macos" in platforms, "Missing macOS target platform in workflow"
    
    assert "x86_64-pc-windows-msvc" in targets, "Missing Windows x64 target triple"
    assert "aarch64-apple-darwin" in targets, "Missing macOS Apple Silicon target triple"

def test_windows_standalone_installers_exist():
    """Verify that both Windows installers were generated and are complete."""
    msi_path = "dist_installers/windows/PlanetariumAI_1.0.0_x64_en-US.msi"
    nsis_path = "dist_installers/windows/PlanetariumAI_1.0.0_x64-setup.exe"
    sidecar_path = "app/src-tauri/binaries/planetarium-ai-server-x86_64-pc-windows-msvc.exe"
    
    assert os.path.exists(sidecar_path), "Frozen sidecar executable does not exist"
    assert os.path.getsize(sidecar_path) > 100 * 1024 * 1024, "Sidecar binary is too small (<100MB)"
    
    assert os.path.exists(msi_path), "MSI installer does not exist"
    assert os.path.getsize(msi_path) > 1024 * 1024 * 1024, "MSI installer is too small (<1GB)"
    
    assert os.path.exists(nsis_path), "NSIS setup installer does not exist"
    assert os.path.getsize(nsis_path) > 1024 * 1024 * 1024, "NSIS installer is too small (<1GB)"

def test_macos_standalone_installer_exists():
    """Verify that the macOS Apple Silicon .dmg installer was generated and downloaded."""
    dmg_path = "dist_installers/macos/PlanetariumAI_1.0.0_aarch64.dmg"
    assert os.path.exists(dmg_path), "macOS Apple Silicon DMG installer does not exist"
    assert os.path.getsize(dmg_path) > 500 * 1024 * 1024, "macOS Apple Silicon DMG installer is too small (<500MB)"
