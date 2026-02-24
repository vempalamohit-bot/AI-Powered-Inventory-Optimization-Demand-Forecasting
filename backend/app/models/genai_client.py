"""Optional GenAI client used by the chat API.

This is deliberately thin and optional:
- If OPENAI_API_KEY / GENAI_MODEL / GENAI_ENABLED are set, it will
  try to call OpenAI's chat completions API.
- If not configured, it simply returns the original answer.

This lets the POC be "GenAI-ready" without breaking local runs.
"""

from __future__ import annotations

import os
from typing import Optional

try:
    # New OpenAI client (python-openai>=1.0.0)
    from openai import OpenAI
except ImportError:  # pragma: no cover - safe fallback when lib not installed
    OpenAI = None  # type: ignore


class GenAIClient:
    """Light wrapper around an LLM provider.

    For now this supports OpenAI-compatible models. If the library or
    API key is missing, it becomes a no-op passthrough.
    """

    def __init__(self) -> None:
        self.enabled_flag = os.getenv("GENAI_ENABLED", "false").lower() == "true"
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("GENAI_MODEL", "gpt-4.1-mini")
        self.client = None  # type: ignore

        if self.enabled_flag and self.api_key and OpenAI is not None:
            self.client = OpenAI(api_key=self.api_key)

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def rewrite_answer(self, question: str, structured_answer: str) -> str:
        """Optionally ask the LLM to turn a structured answer into
        a concise, executive-friendly explanation.
        """
        if not self.enabled or not structured_answer:
            return structured_answer

        try:
            completion = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AI assistant embedded in an inventory "
                            "optimization product. Rewrite the answer in clear, "
                            "executive-friendly business language. Keep it factual, "
                            "concise (max 6 sentences), and avoid technical jargon."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "User question: " + question + "\n\n"
                            "Structured answer from analytics engine: "
                            + structured_answer
                        ),
                    },
                ],
                max_output_tokens=300,
            )

            # New Responses API
            message = completion.output[0].content[0].text
            return message
        except Exception:
            # Fail gracefully and return original text
            return structured_answer

    def analyze_conversation(self, transcript: str) -> str:
        """Use GenAI to analyze a full chat transcript.

        The transcript should be a chronological log of messages
        (user and assistant). The model returns a business-focused
        analysis: summary, key themes, risks, and recommended actions.
        """

        if not self.enabled or not transcript:
            # If GenAI is disabled, just echo back a simple note
            return (
                "GenAI analysis is currently disabled. To enable it, set "
                "GENAI_ENABLED=true and configure OPENAI_API_KEY and GENAI_MODEL."
            )

        try:
            completion = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are an analytics assistant for an inventory "
                            "optimization platform. Given a full chat "
                            "transcript between a business user and the AI "
                            "assistant, provide a concise analysis with: "
                            "1) a short summary, 2) main questions/topics, "
                            "3) any risks or opportunities identified, and "
                            "4) 3-5 concrete follow-up actions for the supply "
                            "chain or finance team."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Here is the chat transcript to analyze:\n\n" + transcript
                        ),
                    },
                ],
                max_output_tokens=600,
            )

            message = completion.output[0].content[0].text
            return message
        except Exception:
            # If analysis fails, degrade gracefully
            return "Unable to run GenAI analysis for this chat transcript at the moment."
