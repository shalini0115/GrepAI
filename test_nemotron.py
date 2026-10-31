"""NVIDIA connectivity check. Skipped when NVIDIA_API_KEY is not set."""
import os

import pytest
import requests

from app.config import settings


@pytest.mark.skipif(not os.getenv("NVIDIA_API_KEY"), reason="NVIDIA_API_KEY not set")
def test_nemotron_responds():
    r = requests.post(
        settings.nvidia_chat_url,
        headers={"Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}"},
        json={
            "model": settings.llm_model,
            "messages": [{"role": "user", "content": "Which number is larger, 9.11 or 9.8?"}],
            "max_tokens": 256,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
        },
        timeout=settings.llm_timeout_seconds,
    )
    assert r.status_code == 200
    assert r.json()["choices"][0]["message"]["content"]