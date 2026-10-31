from contextlib import nullcontext

from music_store import __main__ as cli


def test_configuration_check_never_creates_a_provider_client(monkeypatch, capsys):
    monkeypatch.setenv("GEMINI_API_KEY", "private-test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setattr("sys.argv", ["music_store", "--check-config"])

    def unexpected_client(settings):
        raise AssertionError("No provider client should be created.")

    monkeypatch.setattr(cli, "create_client", unexpected_client)
    assert cli.main() == 0
    output = capsys.readouterr().out
    assert "No model request sent" in output and "private-test-key" not in output


def test_missing_key_is_reported_before_chat(monkeypatch, capsys):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setattr("sys.argv", ["music_store"])
    assert cli.main() == 1
    assert "GEMINI_API_KEY" in capsys.readouterr().out


def test_exit_command_closes_chat_without_a_model_request(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setattr("sys.argv", ["music_store"])
    monkeypatch.setattr(cli, "create_client", lambda settings: nullcontext(object()))
    monkeypatch.setattr("builtins.input", lambda prompt: "exit")
    assert cli.main() == 0
