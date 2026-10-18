import hashlib

import httpx
import pytest
from fastapi.testclient import TestClient

from app import granite
from app.granite import Granite, create_app, grounded, numbers, sha256_of

FACTS = "Patients in active outages: 32. Visits planned: 15 (responders: 5). Waiting: 17. Reserve 2.0 h."


def test_numbers_are_compared_by_value_in_digits_or_words():
    assert numbers("five responders, 2 h, 2.0 h, two") == {5.0, 2.0}
    assert grounded("Five responders cover 15 visits while 17 patients wait.", FACTS)
    assert grounded("Reserve two hours.", FACTS)
    assert not grounded("Five responders cover 16 visits.", FACTS)
    assert not grounded("Power is back by 10:30.", FACTS)


def client(handler) -> Granite:
    return Granite(httpx.AsyncClient(transport=httpx.MockTransport(handler)), "http://granite:8200")


@pytest.mark.anyio
async def test_the_client_returns_only_text_whose_numbers_are_in_the_facts():
    good = client(lambda r: httpx.Response(200, json={"text": "  15 visits planned;\n 17 patients wait. "}))
    assert await good.write("style", FACTS) == "15 visits planned; 17 patients wait."
    invented = client(lambda r: httpx.Response(200, json={"text": "18 patients wait."}))
    assert await invented.write("style", FACTS) is None


@pytest.mark.anyio
async def test_the_client_falls_back_when_granite_is_down_or_broken():
    def unreachable(request):
        raise httpx.ConnectError("no route to granite")

    assert await client(unreachable).write("style", FACTS) is None
    assert await client(lambda r: httpx.Response(500)).write("style", FACTS) is None
    assert await client(lambda r: httpx.Response(200, json={"other": 1})).write("style", FACTS) is None


class FakeLlama:
    def __init__(self):
        self.calls = 0

    def create_chat_completion(self, messages, max_tokens, temperature):
        assert max_tokens == granite.MAX_TOKENS and temperature == 0.0
        self.calls += 1
        return {"choices": [{"message": {"content": "written: " + messages[1]["content"]}}]}


def test_the_server_writes_once_per_prompt_and_caps_its_input():
    llm = FakeLlama()
    web = TestClient(create_app(llm, "granite-test.gguf"))
    assert web.get("/health").json() == {"ok": True, "model": "granite-test.gguf"}
    first = web.post("/write", json={"system": "s", "user": FACTS}).json()
    again = web.post("/write", json={"system": "s", "user": FACTS}).json()
    assert first == {"text": "written: " + FACTS, "cached": False} and again["cached"] and llm.calls == 1
    assert web.post("/write", json={"system": "s", "user": "x" * 4001}).status_code == 422


def test_the_model_file_is_checked_by_its_hash(tmp_path):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"GGUF" * 1000)
    assert sha256_of(model) == hashlib.sha256(b"GGUF" * 1000).hexdigest()
