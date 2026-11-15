"""Google Gemini Developer API provider using google-genai Interactions API."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

from ..config import get_project_root
from .base import PromptAsset


class GeminiProvider:
    """Calls Gemini models via google-genai >= 2.30.1 Interactions API."""

    def __init__(self, *, api_key_env: str = "GEMINI_API_KEY") -> None:
        self.api_key_env = api_key_env

    def _build_client(self) -> Any:
        from google import genai  # lazy import so offline unit tests stay dependency-light

        load_dotenv(get_project_root() / ".env", override=False)
        api_key = os.environ.get(self.api_key_env, "").strip()
        if not api_key:
            raise RuntimeError(f"Missing environment variable: {self.api_key_env}")
        return genai.Client(api_key=api_key)

    def generate_json(
        self,
        *,
        asset: PromptAsset,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        client = self._build_client()
        model = model_override or asset.recommended_model
        interaction = client.interactions.create(
            model=model,
            system_instruction=asset.system_instruction,
            input=json.dumps(payload, ensure_ascii=False),
            response_format=asset.response_schema,
            generation_config={"temperature": asset.temperature},
            store=False,
        )
        text = (interaction.output_text or "").strip()
        return json.loads(text)
