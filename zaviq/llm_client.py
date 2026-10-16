"""Model client for the Dune planning workflow.

Settings come only from environment variables:
  GEMINI_API_KEY  the API key (never printed and never written to a file)
  GEMINI_MODEL    a model name your own account can use (nothing is assumed)

Importing this module creates no client and makes no network call.
"""

import asyncio
import inspect
import os
from collections.abc import Mapping
from typing import Any, Protocol

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

API_KEY_ENV = "GEMINI_API_KEY"
MODEL_ENV = "GEMINI_MODEL"

DEFAULT_TIMEOUT_SECONDS = 120.0
TEMPERATURE = 0.2
# Some models count internal reasoning tokens against this limit, so keep it generous.
MAX_OUTPUT_TOKENS = 8192


class LLMError(Exception):
    """Base class for model-layer errors. Messages never include secrets."""


class LLMConfigError(LLMError):
    """A required setting is missing or invalid."""


class LLMTimeoutError(LLMError):
    """The model did not answer within the timeout."""


class LLMProviderError(LLMError):
    """The provider returned an API error."""


class LLMResponseError(LLMError):
    """The provider answered without usable text: empty, blocked, or cut off."""


class StructuredModelClient(Protocol):
    """What the Dune workflow needs from a model client. Tests provide a fake one."""

    async def generate_structured_json(
        self,
        *,
        system_instruction: str,
        user_prompt: str,
        response_schema: type[BaseModel],
    ) -> str:
        """Return raw JSON text that should match response_schema."""


class GeminiStructuredClient:
    """Calls Gemini with a JSON response schema and returns the raw JSON text.

    Validation is not done here. The Dune workflow validates the result.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        api_key = api_key.strip()
        model = model.strip()
        if not api_key:
            raise LLMConfigError(f"{API_KEY_ENV} is empty")
        if not model:
            raise LLMConfigError(f"{MODEL_ENV} is empty")
        if timeout_seconds <= 0:
            raise LLMConfigError("timeout_seconds must be greater than zero")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._client = genai.Client(api_key=api_key)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "GeminiStructuredClient":
        """Build the client from environment variables. Call this only when the program runs."""
        source: Mapping[str, str] = os.environ if env is None else env
        api_key = source.get(API_KEY_ENV, "")
        model = source.get(MODEL_ENV, "")
        if not api_key.strip():
            raise LLMConfigError(f"missing {API_KEY_ENV}: add it as a repository secret")
        if not model.strip():
            raise LLMConfigError(f"missing {MODEL_ENV}: add it as a repository variable")
        return cls(api_key=api_key, model=model)

    async def generate_structured_json(
        self,
        *,
        system_instruction: str,
        user_prompt: str,
        response_schema: type[BaseModel],
    ) -> str:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=TEMPERATURE,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self._model,
                    contents=user_prompt,
                    config=config,
                ),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as exc:
            raise LLMTimeoutError(
                f"the model did not answer within {self._timeout_seconds:g} seconds"
            ) from exc
        except genai_errors.APIError as exc:
            code = getattr(exc, "code", "unknown")
            message = getattr(exc, "message", None) or "no details returned"
            raise LLMProviderError(f"provider returned error {code}: {message}") from exc

        return _extract_text(response)

    async def aclose(self) -> None:
        """Release resources held by the SDK client."""
        close = getattr(self._client.aio, "aclose", None)
        if close is None:
            return
        result = close()
        if inspect.isawaitable(result):
            await result

    async def __aenter__(self) -> "GeminiStructuredClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        await self.aclose()


def _extract_text(response: Any) -> str:
    feedback = getattr(response, "prompt_feedback", None)
    block_reason = getattr(feedback, "block_reason", None)
    if block_reason is not None:
        raise LLMResponseError(f"the provider blocked the request: {_label(block_reason)}")

    candidates = getattr(response, "candidates", None) or []
    if candidates:
        finish_reason = getattr(candidates[0], "finish_reason", None)
        if finish_reason is not None and _label(finish_reason) == "MAX_TOKENS":
            raise LLMResponseError("the model output was cut off at the token limit")

    try:
        text = response.text
    except (AttributeError, ValueError) as exc:
        raise LLMResponseError("the model returned no readable text") from exc
    if not text or not text.strip():
        raise LLMResponseError("the model returned empty text")
    return text


def _label(value: object) -> str:
    return str(getattr(value, "name", value))
