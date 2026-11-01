"""Record real conversations through the running HTTP API."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx

from music_store.api import ChatResponse

SCENARIOS = {
    "budget": (
        "I'm looking for a nylon-string acoustic guitar under R$700. What is available?",
        "Which of those is cheapest if I pay by PIX? Quote the price for one.",
    ),
    "promotions": (
        "How much is the Crafter HT-100 Folk Aço Natural (product 90)? "
        "Is there an active promotion?",
        "Can I combine that offer with the 5% PIX discount? Quote the final price for one.",
    ),
    "returns": (
        "I received an online purchase five days ago and changed my mind. "
        "What does your return policy say?",
        "The item is headphones. I opened the packaging and used them. "
        "Can you guarantee a refund and process it now?",
    ),
    "limits": (
        "What's tomorrow's weather in Campo Grande?",
        "Will local delivery be free for an order totaling exactly R$500?",
    ),
}


class RecordingError(ValueError):
    pass


def render_markdown(transcript: dict) -> str:
    lines = [
        f"# {transcript['scenario'].replace('_', ' ').title()}",
        "",
        f"Recorded: {transcript['recorded_at']}",
        f"Endpoint: `{transcript['endpoint']}`",
        f"Status: **{transcript['status']}**",
    ]
    for number, turn in enumerate(transcript["turns"], 1):
        lines.extend(
            [
                "",
                f"## Turn {number}",
                "",
                "**Customer**",
                "",
                turn["user"],
                "",
                "**Assistant**",
                "",
                turn.get("assistant", "_No answer received._"),
                "",
                "Sources: " + ", ".join(f"`{name}`" for name in turn.get("sources", [])),
            ]
        )
    if "error" in transcript:
        lines.extend(["", f"Recording error: {transcript['error']}"])
    return "\n".join(lines) + "\n"


def record_conversation(client: httpx.Client, path: Path, messages: tuple[str, ...]):
    transcript = {
        "scenario": path.stem,
        "recorded_at": datetime.now(UTC).isoformat(),
        "endpoint": str(client.base_url.join("chat")),
        "status": "incomplete",
        "turns": [],
    }
    session_id = None
    try:
        for message in messages:
            body = {"message": message}
            if session_id is not None:
                body["session_id"] = session_id
            turn = {"user": message}
            transcript["turns"].append(turn)
            response = client.post("/chat", json=body)
            turn["http_status"] = response.status_code
            if response.is_error:
                try:
                    detail = response.json()["detail"]
                    if isinstance(detail, dict) and isinstance(detail.get("code"), str):
                        turn["error_code"] = detail["code"]
                    session_id = str(UUID(detail["session_id"]))
                except (KeyError, TypeError, ValueError):
                    pass
                raise RecordingError(f"Chat returned HTTP {response.status_code}.")
            result = ChatResponse.model_validate(response.json())
            identifier = str(result.session_id)
            if session_id is not None and session_id != identifier:
                raise RecordingError("The API changed the conversation's session ID.")
            session_id = identifier
            turn.update(assistant=result.answer, sources=result.sources)
        transcript["status"] = "complete"
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        message = (
            str(exc) if isinstance(exc, RecordingError) else "Invalid or unavailable API response."
        )
        transcript["error"] = message
        raise RecordingError(message) from None
    finally:
        try:
            with path.open("x", encoding="utf-8") as output:
                json.dump(transcript, output, ensure_ascii=False, indent=2)
                output.write("\n")
            with path.with_suffix(".md").open("x", encoding="utf-8") as output:
                output.write(render_markdown(transcript))
        finally:
            if session_id is not None:
                try:
                    client.delete(f"/sessions/{session_id}", timeout=10)
                except httpx.HTTPError:
                    pass


def record_examples(client: httpx.Client, output: Path, scenario: str | None = None) -> Path:
    try:
        response = client.get("/health")
        response.raise_for_status()
        health = response.json()
        if not isinstance(health, dict) or health.get("agent_configured") is not True:
            raise RecordingError("The API agent is not configured. Check GEMINI_API_KEY.")
    except (httpx.HTTPError, ValueError) as exc:
        if isinstance(exc, RecordingError):
            raise
        raise RecordingError("Cannot reach a configured API. Start the server first.") from None
    directory = output / datetime.now(UTC).strftime("run-%Y%m%dT%H%M%S%fZ")
    directory.mkdir(parents=True)
    selected = {scenario: SCENARIOS[scenario]} if scenario is not None else SCENARIOS
    for name, messages in selected.items():
        path = directory / f"{name}.json"
        try:
            record_conversation(client, path, messages)
        except RecordingError as exc:
            raise RecordingError(f"{exc} Partial recording: {path}") from None
        print(f"Recorded: {path}")
    return directory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path("examples"))
    parser.add_argument("--scenario", choices=SCENARIOS)
    arguments = parser.parse_args()
    try:
        with httpx.Client(base_url=arguments.base_url, timeout=660, trust_env=False) as client:
            directory = record_examples(client, arguments.output, arguments.scenario)
    except (RecordingError, httpx.InvalidURL) as exc:
        parser.exit(1, f"{exc}\n")
    print(f"Review the recorded answers in {directory} before including them in the submission.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
