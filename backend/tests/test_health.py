"""Tests for GET /health and POST /shutdown endpoints."""


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_is_fast(client):
    """Health endpoint must respond quickly — used for startup polling."""
    import time
    start = time.monotonic()
    client.get("/health")
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, f"Health check took {elapsed:.2f}s — too slow"
