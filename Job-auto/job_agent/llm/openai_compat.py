"""OpenAI-compatible fallback LLM provider and automatic primary/fallback router."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
import yaml
from dotenv import load_dotenv

from ..config import UserConfig, get_project_root
from ..presets import resolve_llm_preset
from .base import LLMProvider, PromptAsset
from .gemini_provider import GeminiProvider

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.DOTALL)


def _strip_json_fences(text: str) -> str:
    clean = (text or "").strip()
    if clean.startswith("```"):
        clean = _JSON_FENCE_RE.sub("", clean).strip()
    return clean


class OpenAICompatibleProvider:
    """Calls any OpenAI-compatible /chat/completions endpoint returning structured JSON."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key_env: str = "FALLBACK_LLM_API_KEY",
        requires_key: bool = True,
        timeout_seconds: float = 45.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()
        self.api_key_env = api_key_env
        self.requires_key = requires_key
        self.timeout_seconds = timeout_seconds
        self._client = client

    def _resolve_api_key(self) -> str:
        load_dotenv(get_project_root() / ".env", override=False)
        key = os.environ.get(self.api_key_env, "").strip() if self.api_key_env else ""
        if not key:
            if not self.requires_key:
                return "local-no-key"
            raise RuntimeError(f"Missing environment variable: {self.api_key_env}")
        return key

    def generate_json(
        self,
        *,
        asset: PromptAsset,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        api_key = self._resolve_api_key()
        target_model = (model_override or self.model or "").strip()
        if not target_model:
            raise RuntimeError("OpenAICompatibleProvider requires a non-empty model name")

        system_msg = (
            f"{asset.system_instruction}\n\n"
            "请严格输出合法的 JSON 对象（不要输出 markdown 解释），必须匹配以下 JSON Schema：\n"
            f"{json.dumps(asset.response_schema, ensure_ascii=False)}"
        )
        body = {
            "model": target_model,
            "temperature": asset.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        }
        own_client = self._client is None
        sess = self._client or httpx.Client(trust_env=False, timeout=self.timeout_seconds)
        try:
            resp = sess.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        finally:
            if own_client:
                sess.close()

        choices = data.get("choices") or []
        if not choices:
            raise ValueError("OpenAI-compatible response contained no choices")
        content = choices[0].get("message", {}).get("content", "")
        return json.loads(_strip_json_fences(content))


class FallbackLLMProvider:
    """Calls primary provider first and falls back transparently on transient/quota errors."""

    def __init__(self, *, primary: LLMProvider, fallback: LLMProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.last_used: str = "primary"
        self.last_primary_error: str = ""

    def generate_json(
        self,
        *,
        asset: PromptAsset,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        try:
            result = self.primary.generate_json(
                asset=asset,
                payload=payload,
                model_override=model_override,
            )
            self.last_used = "primary"
            self.last_primary_error = ""
            return result
        except (RuntimeError, OSError, httpx.HTTPError, ValueError, KeyError) as exc:
            self.last_used = "fallback"
            self.last_primary_error = str(exc)
            # Do not pass a Gemini-specific model name to an OpenAI-compatible fallback backend.
            return self.fallback.generate_json(
                asset=asset,
                payload=payload,
                model_override=None,
            )


def build_llm_provider(
    cfg: UserConfig,
    *,
    project_root: Path | None = None,
) -> LLMProvider:
    """Build user-selected primary LLM provider (Gemini or any OpenAI-compatible) + optional fallback."""
    root = project_root or get_project_root()
    load_dotenv(root / ".env", override=False)

    preset = resolve_llm_preset(cfg.llm.primary_provider)
    if preset["mode"] == "gemini":
        primary: LLMProvider = GeminiProvider(api_key_env=cfg.llm.api_key_env or "GEMINI_API_KEY")
    else:
        primary_base = (
            cfg.llm.base_url
            or os.environ.get("LLM_BASE_URL", "")
            or str(preset.get("base_url") or "")
        ).strip()
        primary_model = (
            cfg.llm.default_model
            or os.environ.get("LLM_MODEL", "")
            or str(preset.get("default_model") or "")
        ).strip()
        primary_env = (cfg.llm.api_key_env or str(preset.get("api_key_env") or "LLM_API_KEY")).strip()
        primary = OpenAICompatibleProvider(
            base_url=primary_base,
            model=primary_model,
            api_key_env=primary_env,
            requires_key=bool(preset.get("requires_key", True)),
        )

    ext_cfg: dict[str, Any] = {}
    ext_path = root / "config" / "extensions.yaml"
    if ext_path.is_file():
        loaded = yaml.safe_load(ext_path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            ext_cfg = loaded.get("llm_providers", {}).get("fallback", {}) or {}

    fallback_enabled = bool(cfg.llm.fallback_enabled or ext_cfg.get("enabled", False))
    base_url = str(
        os.environ.get("FALLBACK_LLM_BASE_URL")
        or cfg.llm.fallback_base_url
        or ext_cfg.get("base_url")
        or ""
    ).strip()
    model = str(
        os.environ.get("FALLBACK_LLM_MODEL")
        or cfg.llm.fallback_model
        or ext_cfg.get("model")
        or ""
    ).strip()
    api_key_env = str(
        cfg.llm.fallback_api_key_env or ext_cfg.get("api_key_env") or "FALLBACK_LLM_API_KEY"
    ).strip()

    if fallback_enabled and base_url and model:
        fallback = OpenAICompatibleProvider(
            base_url=base_url,
            model=model,
            api_key_env=api_key_env,
        )
        return FallbackLLMProvider(primary=primary, fallback=fallback)

    return primary


def test_llm_connection(
    cfg: UserConfig,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Run a tiny JSON ping against the configured primary LLM provider."""
    provider = build_llm_provider(cfg, project_root=project_root)
    asset = PromptAsset(
        task="health_ping",
        prompt_version="1.0",
        recommended_model=cfg.llm.default_model or "gemini-3.5-flash-lite",
        temperature=0.0,
        system_instruction='Return ONLY JSON {"ok": true, "pong": "ready"}.',
        response_schema={
            "type": "object",
            "properties": {"ok": {"type": "boolean"}, "pong": {"type": "string"}},
            "required": ["ok"],
        },
    )
    try:
        res = provider.generate_json(
            asset=asset,
            payload={"ping": "job-auto"},
            model_override=cfg.llm.default_model or None,
        )
        return {
            "ok": True,
            "provider": cfg.llm.primary_provider,
            "model": cfg.llm.default_model,
            "reply": res,
        }
    except (RuntimeError, OSError, httpx.HTTPError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "provider": cfg.llm.primary_provider,
            "model": cfg.llm.default_model,
            "error": str(exc),
        }
