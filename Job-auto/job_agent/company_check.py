"""Deterministic Streamable-HTTP MCP company verification (Tianyancha / Qichacha).

Zero extra LLM tokens: directly invokes MCP JSON-RPC tools over HTTP, parses
structured enterprise registration & risk fields, and caches results in SQLite.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values, load_dotenv

from .config import CompanyCheckConfig, UserConfig, get_project_root
from .db import Database, utc_now_iso

COMPANY_MCP_PRESETS: dict[str, dict[str, str]] = {
    "tianyancha_mcp": {
        "label": "天眼查 MCP (官方 HTTP 网关)",
        "mcp_url": "https://mcp.tianyancha.com/v1",
        "default_key_env": "TYC_MCP_API_KEY",
        "portal_url": "https://ai.tianyancha.com",
        "hint": "直连天眼查 Streamable-HTTP MCP，0 大模型 Token 消耗；需在天眼查 AI 平台免费注册获取 API Key。",
    },
    "qichacha_mcp": {
        "label": "企查查 MCP (官方 HTTP 网关)",
        "mcp_url": "https://agent.qcc.com/mcp/company/stream",
        "default_key_env": "QCC_MCP_TOKEN",
        "portal_url": "https://openapi.qcc.com",
        "hint": "直连企查查企业数据 MCP 网关，0 大模型 Token 消耗；填入 Bearer Token 后自动完成背调缓存。",
    },
    "custom_mcp": {
        "label": "自定义企业背调 MCP (Streamable-HTTP)",
        "mcp_url": "",
        "default_key_env": "COMPANY_MCP_TOKEN",
        "portal_url": "",
        "hint": "支持任何兼容 MCP 2025-03-26 Streamable-HTTP 与 Bearer Token 的企业工商核验服务。",
    },
    "none": {
        "label": "暂不启用企业工商背调",
        "mcp_url": "",
        "default_key_env": "",
        "portal_url": "",
        "hint": "仅运行本地自定义规则与 AI 匹配，不发起外部工商背调请求。",
    },
}

_SEVERE_STATUS_TOKENS = ("注销", "吊销", "清算", "停业", "撤销", "除名", "迁出")
_SEVERE_RISK_TOKENS = ("失信被执行人", "严重违法", "列入严重违法失信", "限制高消费")
_WARN_RISK_TOKENS = ("经营异常", "行政处罚", "欠税公告", "税收违法", "股权出质", "被执行人")
_SOE_OR_LISTED_TAGS = ("国有企业", "央企", "国企", "上市公司", "A股", "港股", "独角兽", "专精特新", "高新技术企业")


def normalize_company_key(company_name: str) -> str:
    """Normalize company display names into stable deduplication keys."""
    raw = str(company_name or "").strip()
    if not raw:
        return ""
    cleaned = re.sub(r"[\s·•\-—_()（）\[\]【】]+", "", raw)
    return cleaned.lower()


def resolve_company_check_endpoint(cfg: UserConfig) -> tuple[str, str]:
    """Return (mcp_url, api_key_env) from CompanyCheckConfig + preset defaults."""
    cc: CompanyCheckConfig = cfg.company_check
    preset = COMPANY_MCP_PRESETS.get(cc.provider, {})
    url = (cc.mcp_url or "").strip() or preset.get("mcp_url", "")
    key_env = (cc.api_key_env or "").strip() or preset.get("default_key_env", "TYC_MCP_API_KEY")
    return url, key_env


def resolve_company_api_key(cfg: UserConfig, *, root: Path | None = None) -> tuple[str, str]:
    """Read (token, env_name) safely from .env / os.environ without leaking elsewhere."""
    _, env_name = resolve_company_check_endpoint(cfg)
    if not env_name:
        return "", ""
    resolved_root = (root or get_project_root()).resolve()
    env_path = resolved_root / ".env"
    load_dotenv(env_path, override=False)
    val = os.environ.get(env_name, "").strip()
    if not val and env_path.is_file():
        vals = dotenv_values(env_path)
        val = str(vals.get(env_name) or "").strip()
    return val, env_name


class McpClientError(RuntimeError):
    """Structured error raised when Streamable-HTTP MCP negotiation or call fails."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _parse_mcp_response_body(resp: httpx.Response) -> dict[str, Any]:
    content_type = (resp.headers.get("content-type") or "").lower()
    raw_text = resp.text or ""
    if "text/event-stream" in content_type or raw_text.lstrip().startswith(("event:", "data:")):
        last_json: dict[str, Any] | None = None
        for line in raw_text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("data:"):
                continue
            payload = stripped[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    last_json = parsed
            except json.JSONDecodeError:
                continue
        if last_json is not None:
            return last_json
        raise McpClientError("invalid_sse", "MCP SSE 响应未能解析出有效 JSON-RPC 数据")
    try:
        parsed = resp.json()
        return parsed if isinstance(parsed, dict) else {"result": parsed}
    except Exception as exc:
        raise McpClientError("invalid_json", f"MCP 响应非 JSON ({resp.status_code}): {raw_text[:180]}") from exc


class StreamableHttpMcpClient:
    """Minimal, self-contained Streamable-HTTP MCP JSON-RPC 2.0 client using httpx."""

    def __init__(
        self,
        mcp_url: str,
        *,
        bearer_token: str = "",
        timeout: float = 18.0,
        client_factory: Callable[[], httpx.Client] | None = None,
    ) -> None:
        self.mcp_url = mcp_url.strip()
        self.bearer_token = bearer_token.strip()
        self.timeout = timeout
        self._client_factory = client_factory
        self._session_id: str = ""
        self._req_id = 0

    def _build_client(self) -> httpx.Client:
        if self._client_factory is not None:
            return self._client_factory()
        # Disable broken Windows proxy env vars when calling domestic HTTPS MCP gateways
        return httpx.Client(trust_env=False, timeout=self.timeout, follow_redirects=True)

    def _headers(self) -> dict[str, str]:
        hdrs = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.bearer_token:
            hdrs["Authorization"] = f"Bearer {self.bearer_token}"
        if self._session_id:
            hdrs["Mcp-Session-Id"] = self._session_id
        return hdrs

    def _post_rpc(
        self,
        client: httpx.Client,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        is_notification: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            body["params"] = params
        if not is_notification:
            self._req_id += 1
            body["id"] = self._req_id

        try:
            resp = client.post(self.mcp_url, json=body, headers=self._headers())
        except httpx.HTTPError as exc:
            raise McpClientError("network_error", f"MCP 网络连接失败：{exc}") from exc

        sid = resp.headers.get("mcp-session-id") or resp.headers.get("Mcp-Session-Id") or ""
        if sid:
            self._session_id = sid.strip()

        if resp.status_code in (401, 403):
            raise McpClientError(
                "auth_failed",
                f"MCP 鉴权失败 (HTTP {resp.status_code})，请检查 API Key / Token 是否有效或已开通对应权益。",
            )
        if resp.status_code == 429:
            raise McpClientError("rate_limited", "MCP 请求触发限流 (HTTP 429)，请稍后再试。")
        if is_notification and resp.status_code in (200, 202, 204):
            return {}
        if resp.status_code >= 400:
            raise McpClientError("http_error", f"MCP 服务端返回 HTTP {resp.status_code}: {resp.text[:200]}")

        data = _parse_mcp_response_body(resp)
        if "error" in data and isinstance(data["error"], dict):
            err = data["error"]
            ecode = str(err.get("code") or "")
            emsg = str(err.get("message") or err)
            if "200001" in ecode or "200001" in emsg:
                raise McpClientError("auth_failed", f"鉴权失败 (200001)：{emsg}")
            if "300008" in ecode or "-32001" in ecode:
                raise McpClientError("rate_limited", f"MCP 接口限流 ({ecode})：{emsg}")
            raise McpClientError("rpc_error", f"MCP 调用错误 ({ecode}): {emsg}")
        return data.get("result") if isinstance(data.get("result"), dict) else data

    def initialize(self, client: httpx.Client) -> dict[str, Any]:
        res = self._post_rpc(
            client,
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "job-auto", "version": "1.8.0"},
            },
        )
        # Send best-effort initialized notification
        try:
            self._post_rpc(client, "notifications/initialized", {}, is_notification=True)
        except McpClientError:
            pass
        return res

    def list_tools(self) -> list[dict[str, Any]]:
        with self._build_client() as client:
            self.initialize(client)
            res = self._post_rpc(client, "tools/list", {})
        tools = res.get("tools") or []
        return [t for t in tools if isinstance(t, dict) and t.get("name")]

    def call_tool_with_client(
        self,
        client: httpx.Client,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        res = self._post_rpc(client, "tools/call", {"name": name, "arguments": arguments})
        return _extract_tool_payload(res)


def _try_parse_json_blob(text: str) -> Any:
    raw = text.strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL).strip()
    if raw.startswith(("{", "[")):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return None


def _extract_tool_payload(res: dict[str, Any]) -> dict[str, Any]:
    """Normalize MCP tools/call result across structuredContent and content[].text."""
    if res.get("isError"):
        texts = [str(c.get("text") or "") for c in res.get("content") or [] if isinstance(c, dict)]
        msg = " ".join(texts).strip() or "MCP tool returned isError=true"
        if "200001" in msg:
            raise McpClientError("auth_failed", f"鉴权失败 (200001)：{msg}")
        if "300008" in msg or "-32001" in msg:
            raise McpClientError("rate_limited", f"MCP 限流：{msg}")
        raise McpClientError("tool_error", msg)

    structured = res.get("structuredContent")
    texts: list[str] = []
    parsed_items: list[Any] = []
    for item in res.get("content") or []:
        if not isinstance(item, dict):
            continue
        t = str(item.get("text") or "").strip()
        if t:
            texts.append(t)
            maybe = _try_parse_json_blob(t)
            if maybe is not None:
                parsed_items.append(maybe)

    return {
        "structured": structured,
        "parsed": parsed_items[0] if len(parsed_items) == 1 else (parsed_items or None),
        "text": "\n".join(texts).strip(),
    }


def _pick_tool(tools: list[dict[str, Any]], preferred_names: tuple[str, ...], keywords: tuple[str, ...]) -> dict[str, Any] | None:
    by_name = {str(t["name"]): t for t in tools}
    for name in preferred_names:
        if name in by_name:
            return by_name[name]
    for t in tools:
        low = str(t["name"]).lower()
        if all(kw in low for kw in keywords):
            return t
    return None


def _build_search_args(tool_def: dict[str, Any] | None, company_name: str) -> dict[str, Any]:
    props = ((tool_def or {}).get("inputSchema") or {}).get("properties") or {}
    args: dict[str, Any] = {}
    matched_key = ""
    for cand in ("keyword", "searchKey", "query", "company_name", "companyName", "name", "keyWord"):
        if cand in props:
            matched_key = cand
            args[cand] = company_name
            break
    if not matched_key:
        args["keyword"] = company_name
    if "page" in props:
        args["page"] = 1
    if "page_size" in props:
        args["page_size"] = 5
    elif "pageSize" in props:
        args["pageSize"] = 5
    return args


def _build_profile_args(
    tool_def: dict[str, Any] | None,
    *,
    company_name: str,
    company_id: str,
) -> dict[str, Any]:
    props = ((tool_def or {}).get("inputSchema") or {}).get("properties") or {}
    args: dict[str, Any] = {}
    if company_id:
        for k in ("company_id", "companyId", "id", "gid", "keyNo"):
            if k in props:
                args[k] = company_id
                break
    for k in ("company_name", "companyName", "name", "keyword", "searchKey"):
        if k in props:
            args[k] = company_name
            break
    if not args:
        if company_id:
            args["company_id"] = company_id
        args["company_name"] = company_name
    return args


def _walk_dicts(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        found.append(node)
        for v in node.values():
            found.extend(_walk_dicts(v))
    elif isinstance(node, list):
        for item in node:
            found.extend(_walk_dicts(item))
    return found


def _extract_candidate_entity(payload: dict[str, Any], target_name: str) -> tuple[str, str]:
    """Extract (company_id, matched_company_name) from search_companies output."""
    target_norm = normalize_company_key(target_name)
    candidates: list[tuple[int, str, str]] = []
    for obj in _walk_dicts(payload.get("structured") or payload.get("parsed")):
        cname = str(
            obj.get("company_name")
            or obj.get("companyName")
            or obj.get("name")
            or obj.get("entName")
            or ""
        ).strip()
        cid = str(
            obj.get("company_id")
            or obj.get("companyId")
            or obj.get("gid")
            or obj.get("keyNo")
            or obj.get("id")
            or ""
        ).strip()
        if not cname and not cid:
            continue
        cnorm = normalize_company_key(cname)
        score = 3 if cnorm == target_norm else (2 if target_norm and target_norm in cnorm else 1)
        candidates.append((score, cid, cname or target_name))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1], candidates[0][2]

    text = str(payload.get("text") or "")
    # Markdown table / text fallback: extract ID & name hints cleanly
    id_match = re.search(r"(?:company_id|企业ID|gid|id)\s*[:：|]\s*`?([A-Za-z0-9_-]{4,})`?", text, re.IGNORECASE)
    return (id_match.group(1) if id_match else ""), target_name


def _has_positive_risk_signal(token: str, full_text: str, dicts: list[dict[str, Any]]) -> bool:
    """Return True only when risk token indicates an actual >0/non-empty risk hit."""
    for d in dicts:
        if token in d:
            val = d[token]
            if isinstance(val, (int, float)):
                return val > 0
            if isinstance(val, list):
                return len(val) > 0
            sval = str(val or "").strip()
            return bool(sval and sval not in {"0", "无", "暂无", "false", "False", "none", "None"})

    if re.search(rf"{token}[\"'`]*\s*[:：|=]\s*(?:0\b|无|暂无|false|\[\s*\]|null)", full_text, re.IGNORECASE):
        return False
    if re.search(rf"{token}[\"'`]*\s*[:：|=]?\s*[1-9]\d*", full_text):
        return True
    return token in full_text


def assess_company_risk(
    *,
    company_name: str,
    matched_company_name: str,
    profile_payload: dict[str, Any],
    search_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministically assess company risk level & factual summary from MCP payloads."""
    merged_blobs = [
        json.dumps(profile_payload.get("structured") or profile_payload.get("parsed") or {}, ensure_ascii=False),
        str(profile_payload.get("text") or ""),
    ]
    if search_payload:
        merged_blobs.append(
            json.dumps(search_payload.get("structured") or search_payload.get("parsed") or {}, ensure_ascii=False)
        )
        merged_blobs.append(str(search_payload.get("text") or ""))
    full_text = "\n".join(x for x in merged_blobs if x)

    dicts = _walk_dicts(profile_payload.get("structured") or profile_payload.get("parsed"))
    if search_payload:
        dicts.extend(_walk_dicts(search_payload.get("structured") or search_payload.get("parsed")))

    reg_status = ""
    staff_count: int | None = None
    establish_date = ""
    reg_capital = ""

    for d in dicts:
        if not reg_status:
            for k in ("regStatus", "reg_status", "status", "entStatus", "经营状态", "登记状态"):
                if d.get(k):
                    reg_status = str(d[k]).strip()
                    break
        if staff_count is None:
            for k in ("socialSecurityStaffNum", "insuredCount", "staffNum", "参保人数"):
                val = d.get(k)
                if val is not None and str(val).strip() != "":
                    m = re.search(r"\d+", str(val))
                    if m:
                        staff_count = int(m.group(0))
                        break
        if not establish_date:
            for k in ("establishTime", "estiblishTime", "startDate", "成立日期"):
                if d.get(k):
                    establish_date = str(d[k]).strip()[:10]
                    break
        if not reg_capital:
            for k in ("regCapital", "reg_capital", "注册资本"):
                if d.get(k):
                    reg_capital = str(d[k]).strip()
                    break

    if not reg_status:
        m = re.search(r"(?:经营状态|登记状态|企业状态)\s*[:：|]\s*([^\s|，,。;；]+)", full_text)
        if m:
            reg_status = m.group(1).strip()
    if staff_count is None:
        m = re.search(r"参保人数\s*[:：|]\s*(\d+)", full_text)
        if m:
            staff_count = int(m.group(1))
    if not establish_date:
        m = re.search(r"成立日期\s*[:：|]\s*(\d{4}-\d{2}-\d{2})", full_text)
        if m:
            establish_date = m.group(1)

    risk_hits_severe: list[str] = [tok for tok in _SEVERE_STATUS_TOKENS if tok in reg_status]
    for tok in _SEVERE_RISK_TOKENS:
        if _has_positive_risk_signal(tok, full_text, dicts):
            risk_hits_severe.append(tok)

    risk_hits_warn: list[str] = []
    for tok in _WARN_RISK_TOKENS:
        if _has_positive_risk_signal(tok, full_text, dicts):
            risk_hits_warn.append(tok)

    tags = [t for t in _SOE_OR_LISTED_TAGS if t in full_text]
    if staff_count == 0 and establish_date:
        try:
            est_dt = datetime.fromisoformat(establish_date)
            if (datetime.now() - est_dt).days < 365:
                risk_hits_warn.append("新设且0参保")
        except ValueError:
            pass

    if risk_hits_severe:
        risk_level = "severe"
    elif risk_hits_warn:
        risk_level = "warning"
    elif reg_status or dicts or len(full_text.strip()) >= 12:
        risk_level = "pass"
    else:
        risk_level = "unknown"

    summary_parts: list[str] = []
    if reg_status:
        summary_parts.append(reg_status)
    if establish_date:
        summary_parts.append(f"{establish_date[:4]}年成立")
    if reg_capital:
        summary_parts.append(f"注册资本{reg_capital}")
    if staff_count is not None:
        summary_parts.append(f"参保{staff_count}人")
    if tags:
        summary_parts.append("/".join(tags[:2]))
    if risk_hits_severe:
        summary_parts.append("高危:" + "、".join(dict.fromkeys(risk_hits_severe)))
    elif risk_hits_warn:
        summary_parts.append("提示:" + "、".join(dict.fromkeys(risk_hits_warn)))
    elif risk_level == "pass":
        summary_parts.append("工商核验正常")

    return {
        "matched_company_name": matched_company_name or company_name,
        "reg_status": reg_status or ("正常" if risk_level == "pass" else ""),
        "risk_level": risk_level,
        "risk_summary": " · ".join(summary_parts) if summary_parts else "已获取工商档案",
        "tags": tags,
        "raw": {
            "staff_count": staff_count,
            "establish_date": establish_date,
            "reg_capital": reg_capital,
            "severe_hits": list(dict.fromkeys(risk_hits_severe)),
            "warn_hits": list(dict.fromkeys(risk_hits_warn)),
        },
    }


def _is_cache_fresh(record: dict[str, Any] | None, *, cache_days: int) -> bool:
    if not record or record.get("risk_level") == "unknown":
        return False
    checked_at = str(record.get("checked_at") or "").strip()
    if not checked_at:
        return False
    try:
        dt = datetime.fromisoformat(checked_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return (datetime.now(UTC) - dt) <= timedelta(days=max(1, int(cache_days)))
    except ValueError:
        return False


def test_company_check_connection(
    cfg: UserConfig,
    *,
    root: Path | None = None,
    client_factory: Callable[[], httpx.Client] | None = None,
) -> dict[str, Any]:
    """Test MCP endpoint connectivity & token auth using initialize + tools/list."""
    cc = cfg.company_check
    if cc.provider == "none":
        return {"status": "disabled", "message": "企业工商背调当前设置为关闭。"}
    url, key_env = resolve_company_check_endpoint(cfg)
    if not url:
        return {"status": "error", "error": "请先填写 MCP 服务端地址 (URL)"}
    token, env_name = resolve_company_api_key(cfg, root=root)
    if not token:
        return {
            "status": "error",
            "error": f"缺少鉴权密钥环境变量 {env_name or key_env}，请在上方输入 API Key / Token 后保存。",
        }
    mcp = StreamableHttpMcpClient(url, bearer_token=token, client_factory=client_factory)
    try:
        tools = mcp.list_tools()
        names = [str(t["name"]) for t in tools]
        return {
            "status": "ok",
            "provider": cc.provider,
            "mcp_url": url,
            "tool_count": len(names),
            "sample_tools": names[:12],
            "message": f"连接成功！已发现 {len(names)} 个 MCP 工具。",
        }
    except McpClientError as exc:
        return {"status": "error", "error_code": exc.code, "error": exc.message}


def verify_company_with_cache(
    db: Database,
    cfg: UserConfig,
    company_name: str,
    *,
    root: Path | None = None,
    force_refresh: bool = False,
    client_factory: Callable[[], httpx.Client] | None = None,
) -> dict[str, Any]:
    """Verify one company via local cache or Streamable-HTTP MCP (0 LLM tokens)."""
    clean_name = str(company_name or "").strip()
    key = normalize_company_key(clean_name)
    if not key or "示例" in clean_name:
        return {
            "company_key": key,
            "company_name": clean_name,
            "risk_level": "unknown",
            "risk_summary": "示例或空企业名，跳过核查",
            "cached": True,
        }

    cc = cfg.company_check
    cached = db.get_company_verification(key)
    if not force_refresh and _is_cache_fresh(cached, cache_days=cc.cache_days):
        return {**cached, "cached": True}

    url, key_env = resolve_company_check_endpoint(cfg)
    token, env_name = resolve_company_api_key(cfg, root=root)
    if not cc.enabled or cc.provider == "none":
        if cached:
            return {**cached, "cached": True}
        return {
            "company_key": key,
            "company_name": clean_name,
            "risk_level": "unknown",
            "risk_summary": "未启用企业背调",
            "cached": False,
        }
    if not url or not token:
        rec = {
            "company_key": key,
            "company_name": clean_name,
            "matched_company_name": "",
            "provider": cc.provider,
            "reg_status": "",
            "risk_level": "unknown",
            "risk_summary": f"未配置 {env_name or key_env}，暂未核验",
            "tags": [],
            "raw": {},
            "source_tools": "",
            "error_message": f"missing_{env_name or key_env}",
            "checked_at": utc_now_iso(),
        }
        return {**rec, "cached": False}

    mcp = StreamableHttpMcpClient(url, bearer_token=token, client_factory=client_factory)
    called_tools: list[str] = []
    try:
        with mcp._build_client() as client:
            mcp.initialize(client)
            tools_res = mcp._post_rpc(client, "tools/list", {})
            tools = [t for t in (tools_res.get("tools") or []) if isinstance(t, dict) and t.get("name")]

            search_tool = _pick_tool(
                tools,
                ("search_companies", "search_company", "verify_company_accuracy", "get_company_profile"),
                ("search", "compan"),
            )
            profile_tool = _pick_tool(
                tools,
                ("get_company_basic_profile", "get_company_registration_info", "get_company_profile", "verify_company_accuracy"),
                ("profile", "compan"),
            )

            search_payload: dict[str, Any] = {}
            matched_id = ""
            matched_name = clean_name
            if search_tool is not None:
                tname = str(search_tool["name"])
                called_tools.append(tname)
                search_payload = mcp.call_tool_with_client(
                    client,
                    tname,
                    _build_search_args(search_tool, clean_name),
                )
                matched_id, matched_name = _extract_candidate_entity(search_payload, clean_name)

            profile_payload = search_payload
            if profile_tool is not None and (
                search_tool is None or str(profile_tool["name"]) != str(search_tool["name"])
            ):
                pname = str(profile_tool["name"])
                called_tools.append(pname)
                profile_payload = mcp.call_tool_with_client(
                    client,
                    pname,
                    _build_profile_args(
                        profile_tool,
                        company_name=matched_name or clean_name,
                        company_id=matched_id,
                    ),
                )

            assessed = assess_company_risk(
                company_name=clean_name,
                matched_company_name=matched_name,
                profile_payload=profile_payload,
                search_payload=search_payload if search_tool else None,
            )
            record = {
                "company_key": key,
                "company_name": clean_name,
                "matched_company_name": assessed["matched_company_name"],
                "provider": cc.provider,
                "reg_status": assessed["reg_status"],
                "risk_level": assessed["risk_level"],
                "risk_summary": assessed["risk_summary"],
                "tags": assessed["tags"],
                "raw": assessed["raw"],
                "source_tools": ", ".join(called_tools),
                "error_message": "",
                "checked_at": utc_now_iso(),
            }
            db.upsert_company_verification(record)
            return {**record, "cached": False}
    except McpClientError as exc:
        record = {
            "company_key": key,
            "company_name": clean_name,
            "matched_company_name": "",
            "provider": cc.provider,
            "reg_status": "",
            "risk_level": "unknown",
            "risk_summary": f"背调暂停：{exc.message}",
            "tags": [],
            "raw": {},
            "source_tools": ", ".join(called_tools),
            "error_message": exc.code,
            "checked_at": utc_now_iso(),
        }
        return {**record, "cached": False}


def verify_candidates_batch(
    db: Database,
    cfg: UserConfig,
    candidates: list[dict[str, Any]],
    *,
    root: Path | None = None,
    client_factory: Callable[[], httpx.Client] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Deduplicate & verify candidate companies before Stage 2 LLM matching."""
    cc = cfg.company_check
    if not cc.enabled or cc.provider == "none":
        return candidates, {"enabled": False, "checked": 0, "cached": 0, "severe_blocked": 0}

    seen_keys: dict[str, dict[str, Any]] = {}
    new_calls = 0
    cache_hits = 0
    severe_blocked = 0
    warnings = 0
    errors = 0

    kept: list[dict[str, Any]] = []
    for job in candidates:
        cname = str(job.get("company") or "").strip()
        key = normalize_company_key(cname)
        if not key:
            kept.append(job)
            continue

        if key not in seen_keys:
            existing = db.get_company_verification(key)
            if _is_cache_fresh(existing, cache_days=cc.cache_days):
                seen_keys[key] = {**existing, "cached": True}
                cache_hits += 1
            elif new_calls < cc.max_companies_per_run:
                res = verify_company_with_cache(
                    db,
                    cfg,
                    cname,
                    root=root,
                    client_factory=client_factory,
                )
                seen_keys[key] = res
                if res.get("error_message"):
                    errors += 1
                else:
                    new_calls += 1
            else:
                seen_keys[key] = {
                    "company_key": key,
                    "company_name": cname,
                    "risk_level": "unknown",
                    "risk_summary": "超出单轮核验上限，保留进入匹配",
                }

        verdict = seen_keys[key]
        level = verdict.get("risk_level", "unknown")
        if level == "warning":
            warnings += 1
        if level == "severe" and cc.auto_reject_severe_risk:
            severe_blocked += 1
            continue
        kept.append(job)

    return kept, {
        "enabled": True,
        "provider": cc.provider,
        "checked_new": new_calls,
        "cached_hits": cache_hits,
        "warnings": warnings,
        "severe_blocked": severe_blocked,
        "errors": errors,
    }


def filter_and_verify_prefilter_candidates(
    db: Database,
    cfg: UserConfig,
    candidates_with_meta: list[tuple[dict[str, Any], Any]],
    *,
    root: Path | None = None,
    client_factory: Callable[[], httpx.Client] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run company MCP check on candidates meeting min_score_to_check and block severe risks."""
    candidate_jobs = [j for j, _ in candidates_with_meta]
    if not cfg.company_check.enabled or cfg.company_check.provider == "none":
        return candidate_jobs, {"enabled": False}

    min_cc = int(cfg.company_check.min_score_to_check or 0)
    to_check = (
        [j for j, out in candidates_with_meta if int(getattr(out, "rule_score_hint", 0) or 0) >= min_cc]
        if min_cc > 0
        else candidate_jobs
    )
    kept_checked, cc_stats = verify_candidates_batch(
        db,
        cfg,
        to_check,
        root=root,
        client_factory=client_factory,
    )
    blocked_ids = {int(j["id"]) for j in to_check} - {int(j["id"]) for j in kept_checked}
    filtered = [j for j in candidate_jobs if int(j["id"]) not in blocked_ids]
    return filtered, cc_stats

