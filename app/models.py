"""Unified LLM calling interface."""

import json
import logging
from typing import Any

from app.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MAX_RETRIES,
    OPENAI_MODEL,
    OPENAI_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)

_llm_instance: Any | None = None


def get_llm() -> Any:
    """Get or create the singleton ChatOpenAI instance."""
    global _llm_instance
    if _llm_instance is None:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "LLM calls require langchain-openai. "
                "Install dependencies with `pip install -r requirements.txt`."
            ) from exc

        _llm_instance = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            model=OPENAI_MODEL,
            temperature=0.3,
            timeout=OPENAI_TIMEOUT_SECONDS,
            max_retries=OPENAI_MAX_RETRIES,
        )
    return _llm_instance


def call_llm(prompt: str, system: str = "") -> str:
    """Call the LLM with a user prompt and optional system message.

    Args:
        prompt: The user message to send.
        system: Optional system message for context.

    Returns:
        The LLM response as a string.

    Raises:
        Exception: Propagated from the LLM call on failure.
    """
    messages = []
    if system:
        messages.append(("system", system))
    messages.append(("human", prompt))

    llm = get_llm()
    logger.debug("Calling LLM with prompt length=%d", len(prompt))
    response = llm.invoke(messages)
    content = str(response.content)
    logger.debug("LLM response length=%d", len(content))
    return content


def call_llm_json(prompt: str, system: str = "") -> dict:
    """Call the LLM and parse the response as JSON.

    The LLM is instructed to return valid JSON. On parse failure,
    a ValueError is raised.

    Args:
        prompt: The user message to send.
        system: Optional system message for context.

    Returns:
        Parsed JSON dict.

    Raises:
        ValueError: If the response cannot be parsed as JSON.
    """
    system_suffix = "\n\nYou MUST respond with valid JSON only. No markdown, no explanation, just JSON."
    full_system = (system or "") + system_suffix

    raw = call_llm(prompt, system=full_system)

    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM did not return valid JSON. Response:\n{raw}") from exc
