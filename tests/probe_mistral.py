"""Diagnose what the Mistral endpoint is actually rejecting.

Separates three possibilities that all surface as a 429: the key has no chat
quota at all, the free tier needs a longer gap between calls, or the request
shape is being refused.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from api import load_env  # noqa: E402

load_env()
KEY = os.environ.get("MISTRAL_API_KEY", "")
URL = "https://api.mistral.ai/v1/chat/completions"
HEAD = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


def show(label: str, response: httpx.Response) -> None:
    interesting = {
        k: v for k, v in response.headers.items()
        if "ratelimit" in k.lower() or "retry" in k.lower()
    }
    print(f"  {label}: HTTP {response.status_code}")
    if interesting:
        print(f"    headers: {interesting}")
    if response.status_code != 200:
        print(f"    body: {response.text[:220]}")


def main() -> int:
    if not KEY:
        print("MISTRAL_API_KEY not set.")
        return 1
    print(f"key loaded: {KEY[:6]}…{KEY[-4:]}\n")

    with httpx.Client(timeout=60) as client:
        print("1. Does the key authenticate at all?")
        show("GET /models", client.get("https://api.mistral.ai/v1/models", headers=HEAD))

        print("\n2. Smallest possible chat call, plain text")
        minimal = {
            "model": "mistral-small-latest",
            "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
            "max_tokens": 5,
        }
        for attempt in range(4):
            response = client.post(URL, headers=HEAD, json=minimal)
            show(f"attempt {attempt + 1}", response)
            if response.status_code == 200:
                print(f"    content: {response.json()['choices'][0]['message']['content']!r}")
                break
            # Give the window a genuinely long time to clear before concluding
            # the key simply has no chat quota.
            time.sleep(15)
        else:
            print("\n    -> four attempts over ~60s all refused.")
            print("    -> the key authenticates but has no usable chat quota.")
            return 2

        print("\n3. Same call with json_schema structured output")
        structured = {
            **minimal,
            "messages": [{"role": "user", "content": "Return {\"ok\": true}"}],
            "max_tokens": 60,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "probe",
                    "schema": {
                        "type": "object",
                        "properties": {"ok": {"type": "boolean"}},
                        "required": ["ok"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
        }
        time.sleep(3)
        response = client.post(URL, headers=HEAD, json=structured)
        show("structured", response)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            print(f"    content: {content!r}")
            print(f"    parses: {json.loads(content)}")
            print("\n    -> structured output works. The adapter is usable.")
            return 0
        print("\n    -> plain chat works but json_schema does not.")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
