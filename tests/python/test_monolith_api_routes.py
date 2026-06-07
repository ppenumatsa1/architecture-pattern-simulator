import importlib.util
import sys
import types
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _load_routes_module() -> types.ModuleType:
    api_dir = Path(__file__).resolve().parents[2] / "monolith" / "api"
    routes_path = api_dir / "routes.py"

    service_stub = types.ModuleType("service")
    service_stub.create_submission = lambda payload: {"payload": payload, "status": "accepted"}
    service_stub.ensure_submission_exists = lambda submission_id: None
    service_stub.get_submission = lambda submission_id: {"submission_id": submission_id}
    service_stub.list_submissions = lambda limit=50, offset=0: {"items": [], "count": 0}

    async def _stream_submission_events(request, submission_id):
        if False:
            yield ""

    service_stub.stream_submission_events = _stream_submission_events

    sys.modules["service"] = service_stub

    spec = importlib.util.spec_from_file_location("test_monolith_routes", routes_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_submissions_route_returns_service_result() -> None:
    routes_module = _load_routes_module()
    app = FastAPI()
    app.include_router(routes_module.router)
    client = TestClient(app)

    response = client.post(
        "/submissions",
        json={"applicantId": "customer-1", "payload": {"amount": 1500}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "payload": {"applicantId": "customer-1", "payload": {"amount": 1500}},
        "status": "accepted",
    }
