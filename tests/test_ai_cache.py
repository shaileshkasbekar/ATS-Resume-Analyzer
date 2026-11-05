"""
Remembered AI answers: the same request reuses the saved answer,
a different request or cache=False asks again.
"""

from types import SimpleNamespace

import resume_parser.ai_client as ai_client


def counting_client(answer='{"score": 70}'):

    calls = {"n": 0}

    def create(**kwargs):
        calls["n"] += 1
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=answer))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    return client, calls


def use_cache(monkeypatch, tmp_path):

    monkeypatch.setattr(ai_client, "CACHE_ENABLED", True)
    monkeypatch.setattr(ai_client, "CACHE_DIR", str(tmp_path))


def test_same_request_is_answered_once(monkeypatch, tmp_path):
    use_cache(monkeypatch, tmp_path)
    client, calls = counting_client()
    monkeypatch.setattr(ai_client, "client", client)

    first = ai_client.ask_ai_for_json("system", "resume A + job X")
    second = ai_client.ask_ai_for_json("system", "resume A + job X")

    assert first == second == {"score": 70}
    assert calls["n"] == 1


def test_changed_resume_is_analysed_again(monkeypatch, tmp_path):
    use_cache(monkeypatch, tmp_path)
    client, calls = counting_client()
    monkeypatch.setattr(ai_client, "client", client)

    ai_client.ask_ai_for_json("system", "resume A + job X")
    ai_client.ask_ai_for_json("system", "resume B + job X")

    assert calls["n"] == 2


def test_generate_new_is_never_cached(monkeypatch, tmp_path):
    use_cache(monkeypatch, tmp_path)
    client, calls = counting_client()
    monkeypatch.setattr(ai_client, "client", client)

    ai_client.ask_ai_for_json("system", "questions", cache=False)
    ai_client.ask_ai_for_json("system", "questions", cache=False)

    assert calls["n"] == 2


def test_failed_answers_are_not_saved(monkeypatch, tmp_path):
    use_cache(monkeypatch, tmp_path)
    client, calls = counting_client("not json")
    monkeypatch.setattr(ai_client, "client", client)

    assert ai_client.ask_ai_for_json("system", "x") is None
    assert ai_client.ask_ai_for_json("system", "x") is None
    assert calls["n"] == 2


def test_cache_off_in_tests_by_default():
    import os
    assert os.environ.get("AI_CACHE") == "0"
