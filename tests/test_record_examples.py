import json
from uuid import uuid4

import httpx
import pytest

from music_store.record_examples import RecordingError, record_examples


def test_recording_keeps_answers_and_sources_reuses_session_and_removes_token(tmp_path):
    identifier = str(uuid4())
    bodies = []
    deleted = []

    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"agent_configured": True})
        if request.method == "DELETE":
            deleted.append(request.url.path)
            return httpx.Response(204)
        bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "session_id": identifier,
                "answer": "Recorded answer with **formatting** and R$408.41.\nSecond line.",
                "sources": ["quote_product"],
            },
        )

    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler)) as client:
        directory = record_examples(client, tmp_path, "budget")
        second_directory = record_examples(client, tmp_path, "budget")
    assert directory != second_directory
    assert "session_id" not in bodies[0]
    assert bodies[1]["session_id"] == identifier
    assert deleted == [f"/sessions/{identifier}"] * 2
    contents = (directory / "budget.json").read_text()
    assert identifier not in contents
    recorded = json.loads(contents)
    assert recorded["status"] == "complete"
    assert len(recorded["turns"]) == 2
    assert recorded["turns"][1]["assistant"].endswith("\nSecond line.")
    assert recorded["turns"][1]["sources"] == ["quote_product"]
    markdown = (directory / "budget.md").read_text()
    assert identifier not in markdown
    assert "Status: **complete**" in markdown
    assert "## Turn 1" in markdown and "## Turn 2" in markdown
    for turn in recorded["turns"]:
        assert turn["user"] in markdown and turn["assistant"] in markdown
    assert "Sources: `quote_product`" in markdown


@pytest.mark.parametrize("failure", ["http", "connection", "invalid_json"])
def test_failure_preserves_partial_conversation_and_stops_run(tmp_path, failure):
    identifier = str(uuid4())
    calls = []
    deleted = []

    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"agent_configured": True})
        if request.method == "DELETE":
            deleted.append(request.url.path)
            return httpx.Response(204)
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(
                200, json={"session_id": identifier, "answer": "First answer.", "sources": []}
            )
        if failure == "connection":
            raise httpx.ReadTimeout("private connection details", request=request)
        if failure == "invalid_json":
            return httpx.Response(200, text="invalid")
        return httpx.Response(429, json={"detail": {"session_id": identifier}})

    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RecordingError, match="Partial recording"):
            record_examples(client, tmp_path)
    files = list(tmp_path.glob("run-*/*.json"))
    assert len(files) == 1 and files[0].name == "budget.json"
    contents = files[0].read_text()
    assert identifier not in contents and "private connection details" not in contents
    recorded = json.loads(contents)
    assert recorded["status"] == "incomplete"
    assert recorded["turns"][0]["assistant"] == "First answer."
    assert "error" in recorded
    assert len(calls) == 2 and deleted == [f"/sessions/{identifier}"]
    markdown = files[0].with_suffix(".md").read_text()
    assert "Status: **incomplete**" in markdown
    assert "First answer." in markdown and "Recording error:" in markdown
    assert identifier not in markdown and "private connection details" not in markdown


def test_unconfigured_api_does_not_create_recordings_or_send_chat_requests(tmp_path):
    requests = []

    def handler(request):
        requests.append(request.url.path)
        return httpx.Response(200, json={"agent_configured": False})

    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RecordingError, match="not configured"):
            record_examples(client, tmp_path)
    assert requests == ["/health"]
    assert not list(tmp_path.iterdir())


def test_first_turn_provider_error_still_cleans_up_the_created_session(tmp_path):
    identifier = str(uuid4())
    deleted = []

    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"agent_configured": True})
        if request.method == "DELETE":
            deleted.append(request.url.path)
            return httpx.Response(204)
        return httpx.Response(
            429, json={"detail": {"session_id": identifier, "code": "rate_limit"}}
        )

    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RecordingError, match="HTTP 429"):
            record_examples(client, tmp_path, "budget")
    recorded = next(tmp_path.glob("run-*/*.json")).read_text()
    assert identifier not in recorded
    assert json.loads(recorded)["status"] == "incomplete"
    assert json.loads(recorded)["turns"][0]["error_code"] == "rate_limit"
    assert deleted == [f"/sessions/{identifier}"]


@pytest.mark.parametrize(
    "body",
    [
        {"session_id": "invalid", "answer": "Answer.", "sources": []},
        {"session_id": str(uuid4()), "answer": None, "sources": []},
        {"session_id": str(uuid4()), "answer": "Answer.", "sources": "get_product"},
    ],
)
def test_malformed_success_cannot_be_marked_as_a_complete_recording(tmp_path, body):
    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"agent_configured": True})
        return httpx.Response(200, json=body)

    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RecordingError, match="Invalid or unavailable"):
            record_examples(client, tmp_path, "budget")
    recorded = json.loads(next(tmp_path.glob("run-*/*.json")).read_text())
    assert recorded["status"] == "incomplete"
    assert "assistant" not in recorded["turns"][0]
