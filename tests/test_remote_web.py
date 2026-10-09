"""Unit tests verifying FastAPI static React mounting, SPA routing, and remote CORS configuration."""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure core is on path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
core_dir = os.path.join(root_dir, "core")
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

from main import app, dist_dir


def test_dist_directory_exists():
    """Verify that the React frontend dist directory has been built."""
    assert os.path.exists(dist_dir), f"Dist directory not found at {dist_dir}"
    assert os.path.exists(os.path.join(dist_dir, "index.html")), "index.html must exist in dist"
    assert os.path.exists(os.path.join(dist_dir, "audio-processor.js")), "audio-processor.js must exist in dist"


def test_serve_root_index_html():
    """Verify that GET / returns the built React index.html."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "PlanetariumAI" in response.text or "root" in response.text


def test_serve_audio_processor():
    """Verify that GET /audio-processor.js returns the worklet file."""
    client = TestClient(app)
    response = client.get("/audio-processor.js")
    assert response.status_code == 200
    assert "AudioWorkletProcessor" in response.text or "registerProcessor" in response.text


def test_serve_spa_fallback():
    """Verify that client-side SPA routes fallback to index.html."""
    client = TestClient(app)
    response = client.get("/astronomy/kiosk/view")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<!doctype html>" in response.text.lower() or "<html" in response.text.lower()


def test_cors_remote_headers():
    """Verify that CORS middleware accepts remote origins."""
    client = TestClient(app)
    response = client.options(
        "/",
        headers={
            "Origin": "https://planetarium.my-cloudflare-tunnel.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    # CORS middleware returns Access-Control-Allow-Origin: * or the request origin
    assert response.headers.get("access-control-allow-origin") in (
        "*",
        "https://planetarium.my-cloudflare-tunnel.com"
    )
