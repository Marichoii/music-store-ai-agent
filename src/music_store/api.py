"""Expose the agent through FastAPI."""

from contextlib import asynccontextmanager
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from music_store.agent import StoreAgent, create_client
from music_store.catalog import Catalog, CatalogError
from music_store.config import ConfigurationError, Settings
from music_store.policies import PolicyBook, PolicyError
from music_store.sessions import SessionError, SessionStore
from music_store.tools import StoreTools


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [{"message": "Which nylon-string guitars do you have under R$700?"}]
        },
    )
    message: str = Field(min_length=1, max_length=4000)
    session_id: UUID | None = Field(
        default=None, description="Omit for a new chat; reuse the returned ID for follow-ups."
    )


class ChatResponse(BaseModel):
    session_id: UUID
    answer: str
    sources: list[str]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    agent_configured: bool


def create_app(
    agent: StoreAgent | None = None,
    settings: Settings | None = None,
    sessions: SessionStore | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        client = None
        application.state.agent = agent
        application.state.setup_error = None
        application.state.sessions = sessions if sessions is not None else SessionStore()
        if agent is None:
            try:
                configuration = settings or Settings.from_env()
                configuration.require_api_key()
                tools = StoreTools(Catalog.load(), PolicyBook())
                client = create_client(configuration)
                application.state.agent = StoreAgent(client, configuration, tools)
            except (ConfigurationError, CatalogError, PolicyError) as exc:
                application.state.setup_error = str(exc)
            except Exception:
                application.state.setup_error = "The agent could not be initialized."
        try:
            yield
        finally:
            application.state.sessions.clear()
            if client is not None:
                client.close()

    application = FastAPI(title="Empório da Música API", version="0.1.0", lifespan=lifespan)

    @application.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return RedirectResponse("/docs")

    @application.exception_handler(SessionError)
    def session_error(request, exc: SessionError):
        status = {"session_not_found": 404, "session_busy": 409, "session_limit": 503}[exc.code]
        return JSONResponse(
            status_code=status, content={"detail": {"code": exc.code, "message": str(exc)}}
        )

    @application.get("/health")
    def health() -> HealthResponse:
        return HealthResponse(agent_configured=application.state.agent is not None)

    @application.post("/chat")
    def chat(body: ChatRequest) -> ChatResponse:
        current = application.state.agent
        if current is None:
            raise HTTPException(
                status_code=503,
                detail={"code": "not_configured", "message": application.state.setup_error},
            )
        with application.state.sessions.use(body.session_id) as (identifier, conversation):
            try:
                result = current.reply(body.message, conversation)
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "code": "internal",
                        "message": "The request could not be completed.",
                        "session_id": str(identifier),
                    },
                ) from None
            if not result.ok:
                status = {
                    "invalid_message": 422,
                    "authentication": 503,
                    "rate_limit": 429,
                    "internal": 500,
                }.get(result.error_code, 502)
                raise HTTPException(
                    status_code=status,
                    detail={
                        "code": result.error_code,
                        "message": result.answer,
                        "session_id": str(identifier),
                    },
                )
            return ChatResponse(
                session_id=identifier,
                answer=result.answer,
                sources=sorted({trace.name for trace in result.traces if trace.result.get("ok")}),
            )

    @application.delete("/sessions/{session_id}", status_code=204)
    def delete_session(session_id: UUID) -> Response:
        application.state.sessions.delete(session_id)
        return Response(status_code=204)

    return application


app = create_app()
