"""Keep bounded conversation state in one server process."""

from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from uuid import UUID, uuid4

from music_store.agent import Conversation


class SessionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class Session:
    conversation: Conversation = field(default_factory=Conversation)
    last_used: float = 0
    lock: Lock = field(default_factory=Lock)


class SessionStore:
    def __init__(self, max_sessions: int = 100, ttl_seconds: int = 1800, clock=monotonic):
        if max_sessions < 1 or ttl_seconds <= 0:
            raise ValueError("Session capacity and lifetime must be positive.")
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self._sessions: dict[UUID, Session] = {}
        self._lock = Lock()

    def _prune(self, now: float):
        for identifier, session in tuple(self._sessions.items()):
            if now - session.last_used >= self.ttl_seconds and not session.lock.locked():
                del self._sessions[identifier]

    @contextmanager
    def use(self, session_id: UUID | None = None):
        with self._lock:
            now = self.clock()
            self._prune(now)
            if session_id is None:
                if len(self._sessions) >= self.max_sessions:
                    raise SessionError(
                        "session_limit", "Session capacity reached. Try again later."
                    )
                session_id = uuid4()
                self._sessions[session_id] = Session(last_used=now)
            session = self._sessions.get(session_id)
            if session is None:
                raise SessionError(
                    "session_not_found", "Session not found or expired. Start a new chat."
                )
            if not session.lock.acquire(blocking=False):
                raise SessionError("session_busy", "A message is already running in this session.")
            session.last_used = now
        try:
            yield session_id, session.conversation
        finally:
            with self._lock:
                session.last_used = self.clock()
                session.lock.release()

    def delete(self, session_id: UUID):
        with self._lock:
            self._prune(self.clock())
            session = self._sessions.get(session_id)
            if session is None:
                raise SessionError("session_not_found", "Session not found or expired.")
            if session.lock.locked():
                raise SessionError("session_busy", "Wait for the current message before deleting.")
            del self._sessions[session_id]

    def clear(self):
        with self._lock:
            self._sessions.clear()
