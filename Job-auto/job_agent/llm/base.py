"""Prompt asset loader (from prompts/<task>/) and LLMProvider protocol."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml


@dataclass(frozen=True)
class PromptAsset:
    task: str
    prompt_version: str
    recommended_model: str
    temperature: float
    system_instruction: str
    response_schema: dict[str, Any]


class LLMProvider(Protocol):
    def generate_json(
        self,
        *,
        asset: PromptAsset,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        """Execute structured JSON inference against the configured model backend."""


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def load_prompt_asset(prompts_root: Path, task: str) -> PromptAsset:
    task_dir = prompts_root / task
    system_raw = (task_dir / "system.md").read_text(encoding="utf-8")
    schema_raw = (task_dir / "schema.json").read_text(encoding="utf-8")

    meta: dict[str, Any] = {}
    body = system_raw
    match = _FRONTMATTER_RE.match(system_raw)
    if match:
        meta = yaml.safe_load(match.group(1)) or {}
        body = match.group(2).strip()

    return PromptAsset(
        task=str(meta.get("task") or task),
        prompt_version=str(meta.get("prompt_version") or "v1.0"),
        recommended_model=str(meta.get("recommended_model") or "gemini-3.8-flash"),
        temperature=float(meta.get("temperature", 0.0)),
        system_instruction=body,
        response_schema=json.loads(schema_raw),
    )
