"""Local API contract tests: endpoints, Host/Origin enforcement, run flow.

These verify the security controls on the local API — loopback binding,
Host/Origin checks, and that a run can be created and its evidence exported.
They use an isolated data dir so they don't touch the user's real store.
"""
import pytest

from agentcrash.server.api import create_app

try:
    from fastapi.testclient import TestClient
    HAS_TESTCLIENT = True
except Exception:  # pragma: no cover
    HAS_TESTCLIENT = False


HOST_OK = {"Host": "127.0.0.1:8000"}


@pytest.fixture
def client(tmp_path):
    app = create_app(data_dir=str(tmp_path / "data"))
    return TestClient(app, base_url="http://127.0.0.1:8000")


@pytest.mark.skipif(not HAS_TESTCLIENT, reason="fastapi testclient unavailable")
def test_forbidden_host_rejected(client):
    r = client.get("/v1/capabilities", headers={"Host": "evil.example.com"})
    assert r.status_code == 403


@pytest.mark.skipif(not HAS_TESTCLIENT, reason="fastapi testclient unavailable")
def test_capabilities(client):
    r = client.get("/v1/capabilities", headers=HOST_OK)
    assert r.status_code == 200
    assert "documents.read" in r.json()["tools"]


@pytest.mark.skipif(not HAS_TESTCLIENT, reason="fastapi testclient unavailable")
def test_scenarios_listed(client):
    r = client.get("/v1/scenarios", headers=HOST_OK)
    assert r.status_code == 200
    assert "invoice-confidential-note" in r.json()["scenarios"]


@pytest.mark.skipif(not HAS_TESTCLIENT, reason="fastapi testclient unavailable")
def test_run_create_and_events(client):
    r = client.post("/v1/runs",
                    json={"scenario_id": "invoice-confidential-note", "variant": "attack"},
                    headers=HOST_OK)
    assert r.status_code == 200
    dims = r.json()["dimensions"]
    assert dims["attack_succeeded"] is True
    run_id = r.json()["run_id"]
    ev = client.get(f"/v1/runs/{run_id}/events", headers=HOST_OK)
    assert ev.status_code == 200
    assert len(ev.json()["events"]) >= 5


@pytest.mark.skipif(not HAS_TESTCLIENT, reason="fastapi testclient unavailable")
def test_cross_origin_mutation_blocked(client):
    r = client.post("/v1/runs",
                    json={"scenario_id": "invoice-confidential-note"},
                    headers={**HOST_OK, "Origin": "https://evil.example.com"})
    assert r.status_code == 403


@pytest.mark.skipif(not HAS_TESTCLIENT, reason="fastapi testclient unavailable")
def test_export_json(client):
    r = client.post("/v1/runs",
                    json={"scenario_id": "invoice-confidential-note", "variant": "benign"},
                    headers=HOST_OK)
    run_id = r.json()["run_id"]
    e = client.post(f"/v1/runs/{run_id}/exports", json={"format": "json"}, headers=HOST_OK)
    assert e.status_code == 200
    body = e.json()
    assert "dimensions" in body and "events" in body