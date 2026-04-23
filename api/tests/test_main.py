import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """Return a TestClient with Redis fully mocked."""
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.hget.return_value = b"queued"

    with patch("main.r", mock_redis):
        from main import app
        yield TestClient(app), mock_redis


def test_health_ok(client):
    tc, mock_r = client
    mock_r.ping.return_value = True
    resp = tc.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_job_returns_job_id(client):
    tc, mock_r = client
    resp = tc.post("/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    mock_r.lpush.assert_called_once()
    mock_r.hset.assert_called_once()


def test_create_job_pushes_to_correct_queue(client):
    tc, mock_r = client
    resp = tc.post("/jobs")
    job_id = resp.json()["job_id"]
    mock_r.lpush.assert_called_with("jobs", job_id)


def test_get_job_status(client):
    tc, mock_r = client
    mock_r.hget.return_value = b"queued"
    fake_id = "aaaaaaaa-0000-0000-0000-000000000000"
    resp = tc.get(f"/jobs/{fake_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["job_id"] == fake_id


def test_get_job_not_found(client):
    tc, mock_r = client
    mock_r.hget.return_value = None
    resp = tc.get("/jobs/nonexistent-id")
    assert resp.status_code == 404


def test_health_redis_down(client):
    tc, mock_r = client
    import redis as redis_lib
    mock_r.ping.side_effect = redis_lib.exceptions.ConnectionError("down")
    resp = tc.get("/healthz")
    assert resp.status_code == 503