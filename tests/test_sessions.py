from uuid import uuid4

import pytest

from music_store.sessions import SessionError, SessionStore


def test_conversations_have_independent_state():
    store = SessionStore()
    with store.use() as (first_id, first):
        with store.use() as (second_id, second):
            assert first_id != second_id and first is not second
            first.turns.append([])
            assert not second.turns
    with store.use(first_id) as (_, restored):
        assert restored is first and len(restored.turns) == 1


def test_busy_session_rejects_parallel_use_and_deletion():
    store = SessionStore()
    with store.use() as (identifier, _):
        with pytest.raises(SessionError, match="already running"):
            with store.use(identifier):
                pass
        with pytest.raises(SessionError, match="Wait"):
            store.delete(identifier)
    store.delete(identifier)
    with pytest.raises(SessionError, match="not found"):
        with store.use(identifier):
            pass


def test_idle_sessions_expire_and_free_capacity():
    now = [0.0]
    store = SessionStore(max_sessions=1, ttl_seconds=10, clock=lambda: now[0])
    with store.use() as (original_id, _):
        pass
    with pytest.raises(SessionError, match="capacity"):
        with store.use():
            pass
    now[0] = 11
    with pytest.raises(SessionError, match="expired"):
        with store.use(original_id):
            pass
    with store.use() as (new_id, _):
        assert new_id != original_id


def test_active_request_does_not_expire_and_failure_releases_lock():
    now = [0.0]
    store = SessionStore(max_sessions=1, ttl_seconds=10, clock=lambda: now[0])
    with pytest.raises(RuntimeError):
        with store.use() as (identifier, _):
            now[0] = 20
            with pytest.raises(SessionError, match="capacity"):
                with store.use():
                    pass
            raise RuntimeError("request failed")
    with store.use(identifier):
        pass


def test_unknown_ids_are_not_created_and_shutdown_clears_state():
    store = SessionStore()
    with pytest.raises(SessionError):
        store.delete(uuid4())
    with store.use() as (identifier, _):
        pass
    store.clear()
    with pytest.raises(SessionError):
        with store.use(identifier):
            pass
