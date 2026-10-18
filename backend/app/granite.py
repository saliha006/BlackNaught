"""F8 Granite (Ahmed): IBM Granite 3.3 2B Instruct (big-endian GGUF, Q4_K_M) writes the agent's words, never its choices.

One process holds the model (`python -m app.granite`, the `granite` service in infra/granite.yml). It refuses to start
unless the model file matches its pinned SHA-256, and it answers POST /write on an internal network only the agent
joins. The agent hands it the facts of a decision already made; text that carries a number those facts don't is
rejected and the agent keeps its template. With Granite gone the decisions are the same; only the wording changes.
"""
import hashlib
import logging
import os
import re
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger(__name__)

PORT = 8200
MAX_TOKENS = 200
THREADS = 2
CACHE_SIZE = 256
NUMBER = re.compile(r"\d+(?:\.\d+)?")
WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen"
                                     " fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}


def numbers(text: str) -> set[float]:
    """Every number in the text, digits or words, as values ('2', '2.0' and 'two' are the same number)."""
    found = {float(n) for n in NUMBER.findall(text)}
    return found | {float(WORDS[w]) for w in re.findall(r"[a-z]+", text.lower()) if w in WORDS}


def grounded(text: str, facts: str) -> bool:
    return numbers(text) <= numbers(facts)


class Granite:
    """Client for the granite service. write() gives None whenever there's no usable text, so the caller falls back."""

    def __init__(self, client: httpx.AsyncClient, url: str):
        self.client = client
        self.url = url.rstrip("/")

    async def write(self, system: str, facts: str) -> str | None:
        try:
            resp = await self.client.post(f"{self.url}/write", json={"system": system, "user": facts}, timeout=150)
            resp.raise_for_status()
            text = " ".join(resp.json()["text"].split())
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            log.warning("granite gave no text (%s); keeping the template", exc)
            return None
        if not text or not grounded(text, facts):
            log.warning("granite text rejected: a number in it isn't in the facts; keeping the template")
            return None
        return text


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 22):
            digest.update(chunk)
    return digest.hexdigest()


def create_app(llm: Any, model_name: str):
    from fastapi import FastAPI
    from pydantic import BaseModel, Field

    class Ask(BaseModel):
        system: str = Field(max_length=2000)
        user: str = Field(max_length=4000)

    app = FastAPI()
    cache: OrderedDict[str, str] = OrderedDict()
    lock = threading.Lock()  # one llama.cpp context, and FastAPI runs sync endpoints on a thread pool

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "model": model_name}

    @app.post("/write")
    def write(ask: Ask) -> dict[str, Any]:
        key = hashlib.sha256(f"{ask.system}\0{ask.user}".encode()).hexdigest()
        with lock:
            if key in cache:
                cache.move_to_end(key)
                return {"text": cache[key], "cached": True}
            out = llm.create_chat_completion(
                messages=[{"role": "system", "content": ask.system}, {"role": "user", "content": ask.user}],
                max_tokens=MAX_TOKENS, temperature=0.0)
            text = out["choices"][0]["message"]["content"]
            cache[key] = text
            if len(cache) > CACHE_SIZE:
                cache.popitem(last=False)
        return {"text": text, "cached": False}

    return app


def main() -> None:
    import uvicorn
    from llama_cpp import Llama  # only this process loads the model

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    model = Path(os.environ["BN_GRANITE_MODEL"])
    if (actual := sha256_of(model)) != os.environ["BN_GRANITE_SHA256"]:
        raise SystemExit(f"granite: {model.name} has SHA-256 {actual}, not the pinned one; refusing to load it")
    llm = Llama(model_path=str(model), n_ctx=2048, n_threads=THREADS, verbose=False)
    uvicorn.run(create_app(llm, model.name), host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
