import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from google import genai
from google.genai import types

from music_store import api
from music_store.agent import StoreAgent, ToolTrace, TurnResult
from music_store.catalog import CatalogError
from music_store.config import Settings
from music_store.sessions import SessionStore


class FakeAgent:
    def __init__(self):
        self.calls = 0
        self.failure = None
        self.started = Event()
        self.release = Event()

    def reply(self, message, conversation):
        self.calls += 1
        if message == "wait":
            self.started.set()
            if not self.release.wait(timeout=5):
                raise RuntimeError("Test request timed out.")
        if isinstance(self.failure, Exception):
            raise self.failure
        if self.failure:
            return TurnResult("Safe provider error.", False, error_code=self.failure)
        previous = [
            part.text
            for turn in conversation.turns
            for content in turn
            for part in content.parts
            if part.text
        ]
        conversation.turns.append([types.Content(role="user", parts=[types.Part(text=message)])])
        trace = ToolTrace("get_product", {"query": "81"}, {"ok": True})
        return TurnResult(" | ".join([*previous, message]), True, (trace,))


def test_chat_reuses_its_session_and_delete_removes_history():
    agent = FakeAgent()
    with TestClient(api.create_app(agent=agent)) as client:
        first = client.post("/chat", json={"message": "First session"}).json()
        second = client.post("/chat", json={"message": "Second session"}).json()
        assert UUID(first["session_id"]) != UUID(second["session_id"])
        response = client.post(
            "/chat", json={"message": "Follow-up", "session_id": first["session_id"]}
        )
        assert response.status_code == 200
        assert response.json()["answer"] == "First session | Follow-up"
        assert response.json()["sources"] == ["get_product"]
        assert client.delete(f"/sessions/{first['session_id']}").status_code == 204
        assert (
            client.post(
                "/chat", json={"message": "Again", "session_id": first["session_id"]}
            ).status_code
            == 404
        )


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"message": ""},
        {"message": "  "},
        {"message": "x" * 4001},
        {"message": 1},
        {"message": None},
        {"message": "Hi", "session_id": "invalid"},
        {"message": "Hi", "extra": True},
    ],
)
def test_invalid_body_is_rejected_before_the_agent(body):
    agent = FakeAgent()
    with TestClient(api.create_app(agent=agent)) as client:
        assert client.post("/chat", json=body).status_code == 422
        assert agent.calls == 0


@pytest.mark.parametrize(
    "code,status",
    [
        ("authentication", 503),
        ("rate_limit", 429),
        ("connection", 502),
        ("provider", 502),
        ("no_evidence", 502),
        ("internal", 500),
    ],
)
def test_failures_have_http_status_and_a_reusable_session(code, status):
    agent = FakeAgent()
    agent.failure = code
    with TestClient(api.create_app(agent=agent)) as client:
        response = client.post("/chat", json={"message": "Failed message"})
        assert response.status_code == status
        detail = response.json()["detail"]
        assert detail["code"] == code
        identifier = detail["session_id"]
        assert UUID(identifier)
        agent.failure = None
        retry = client.post("/chat", json={"message": "Retry", "session_id": identifier})
        assert retry.status_code == 200 and retry.json()["answer"] == "Retry"


def test_unexpected_failure_does_not_leak_exception_details():
    agent = FakeAgent()
    agent.failure = RuntimeError("private-error-details")
    with TestClient(api.create_app(agent=agent)) as client:
        response = client.post("/chat", json={"message": "Hi"})
        assert response.status_code == 500 and "private-error-details" not in response.text


def test_missing_key_keeps_health_and_documentation_available():
    with TestClient(api.create_app(settings=Settings(api_key=""))) as client:
        assert client.get("/health").json() == {"status": "ok", "agent_configured": False}
        assert client.get("/docs").status_code == 200
        response = client.post("/chat", json={"message": "Hi"})
        assert response.status_code == 503
        assert "GEMINI_API_KEY" in response.json()["detail"]["message"]


def test_capacity_and_expiry_are_enforced_over_http():
    now = [0.0]
    sessions = SessionStore(max_sessions=1, ttl_seconds=10, clock=lambda: now[0])
    with TestClient(api.create_app(agent=FakeAgent(), sessions=sessions)) as client:
        first = client.post("/chat", json={"message": "Hi"}).json()
        assert client.post("/chat", json={"message": "New chat"}).status_code == 503
        now[0] = 11
        assert (
            client.post(
                "/chat", json={"message": "Old", "session_id": first["session_id"]}
            ).status_code
            == 404
        )
        assert client.post("/chat", json={"message": "New chat"}).status_code == 200


def test_unknown_and_other_application_session_ids_are_rejected():
    with TestClient(api.create_app(agent=FakeAgent())) as first:
        with TestClient(api.create_app(agent=FakeAgent())) as second:
            identifier = first.post("/chat", json={"message": "Hi"}).json()["session_id"]
            assert (
                second.post("/chat", json={"message": "Hi", "session_id": identifier}).status_code
                == 404
            )
            assert first.delete(f"/sessions/{uuid4()}").status_code == 404


def test_concurrent_requests_do_not_mix_or_block_other_sessions():
    agent = FakeAgent()
    with TestClient(api.create_app(agent=agent)) as client:
        identifier = client.post("/chat", json={"message": "First"}).json()["session_id"]
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                client.post, "/chat", json={"message": "wait", "session_id": identifier}
            )
            try:
                assert agent.started.wait(timeout=2)
                assert (
                    client.post(
                        "/chat", json={"message": "Concurrent", "session_id": identifier}
                    ).status_code
                    == 409
                )
                assert client.delete(f"/sessions/{identifier}").status_code == 409
                assert client.get("/health").status_code == 200
                assert client.post("/chat", json={"message": "Independent"}).status_code == 200
            finally:
                agent.release.set()
            assert pending.result(timeout=2).status_code == 200


def test_sources_are_initialized_once_and_provider_client_is_closed(monkeypatch):
    class Client:
        closed = False

        def close(self):
            self.closed = True

    provider = Client()
    monkeypatch.setattr(api, "create_client", lambda settings: provider)
    monkeypatch.setattr(api, "StoreAgent", lambda client, settings, tools: FakeAgent())
    with TestClient(api.create_app(settings=Settings(api_key="test-key"))) as client:
        assert client.get("/health").json()["agent_configured"]
        schema = client.get("/openapi.json").json()
        assert {"/chat", "/health", "/sessions/{session_id}"}.issubset(schema["paths"])
        assert "api_key" not in schema["components"]["schemas"]["ChatRequest"]["properties"]
        assert not provider.closed
    assert provider.closed


def test_source_failure_produces_an_actionable_unavailable_response(monkeypatch):
    def fail():
        raise CatalogError("Catalog source unavailable.")

    monkeypatch.setattr(api.Catalog, "load", fail)
    with TestClient(api.create_app(settings=Settings(api_key="test-key"))) as client:
        response = client.post("/chat", json={"message": "Hi"})
        assert response.status_code == 503
        assert response.json()["detail"]["message"] == "Catalog source unavailable."


def test_http_request_reaches_real_agent_tools_and_sdk_with_mocked_provider(store_tools):
    payloads = [
        {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {
                        "role": "model",
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "quote_product",
                                    "id": "call-1",
                                    "args": {"product_id": 81, "payment_method": "pix"},
                                },
                                "thoughtSignature": "c2lnbmF0dXJl",
                            }
                        ],
                    },
                }
            ]
        },
        {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {
                        "role": "model",
                        "parts": [{"text": "Yamaha C40: BRL 569.91 with PIX."}],
                    },
                }
            ]
        },
    ]
    requests = []

    def transport(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=payloads.pop(0), request=request)

    with genai.Client(
        api_key="test-key",
        http_options=types.HttpOptions(
            httpx_client=httpx.Client(transport=httpx.MockTransport(transport))
        ),
    ) as provider:
        agent = StoreAgent(provider, Settings(api_key="unused"), store_tools)
        with TestClient(api.create_app(agent=agent)) as client:
            response = client.post("/chat", json={"message": "Yamaha C40 with PIX?"})
            assert response.status_code == 200
            assert response.json()["sources"] == ["quote_product"]
            assert UUID(response.json()["session_id"])
    assert len(requests) == 2
    result = requests[1]["contents"][-1]["parts"][0]["functionResponse"]["response"]
    assert result["data"]["subtotal_brl"] == "569.91"
