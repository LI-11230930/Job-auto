"""Tests for Streamable-HTTP MCP company verification (Tianyancha / Qichacha) & Stage 2 integration."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import httpx


def _build_mock_mcp_transport(calls_log: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") == "Bearer tyc-test-token-123"
        body = json.loads(request.content.decode("utf-8"))
        method = body.get("method")
        req_id = body.get("id")
        calls_log.append(str(method))

        if method == "initialize":
            return httpx.Response(
                200,
                headers={"mcp-session-id": "sess-tyc-001", "content-type": "application/json"},
                json={
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2025-03-26",
                        "serverInfo": {"name": "tyc-mcp-mock", "version": "1.0"},
                    },
                },
            )
        assert request.headers.get("mcp-session-id") == "sess-tyc-001"

        if method == "notifications/initialized":
            return httpx.Response(202, json={})

        if method == "tools/list":
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {
                                "name": "search_companies",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "keyword": {"type": "string"},
                                        "page": {"type": "integer"},
                                        "page_size": {"type": "integer"},
                                    },
                                },
                            },
                            {
                                "name": "get_company_basic_profile",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "company_id": {"type": "string"},
                                        "company_name": {"type": "string"},
                                    },
                                },
                            },
                        ]
                    },
                },
            )

        if method == "tools/call":
            params = body.get("params") or {}
            tname = params.get("name")
            args = params.get("arguments") or {}
            calls_log.append(f"tool:{tname}")
            if tname == "search_companies":
                kw = str(args.get("keyword") or "")
                # Return SSE stream framing to prove both SSE and JSON work
                if "高危注销" in kw:
                    res_payload = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(
                                        {
                                            "items": [
                                                {
                                                    "company_id": "tyc-bad-999",
                                                    "company_name": "高危注销空壳科技有限公司",
                                                }
                                            ]
                                        },
                                        ensure_ascii=False,
                                    ),
                                }
                            ]
                        },
                    }
                else:
                    res_payload = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(
                                        {
                                            "items": [
                                                {
                                                    "company_id": "tyc-good-001",
                                                    "company_name": "星图国有控股集团股份有限公司",
                                                }
                                            ]
                                        },
                                        ensure_ascii=False,
                                    ),
                                }
                            ]
                        },
                    }
                sse = f"event: message\ndata: {json.dumps(res_payload, ensure_ascii=False)}\n\n"
                return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=sse)

            if tname == "get_company_basic_profile":
                cid = str(args.get("company_id") or "")
                if cid == "tyc-bad-999":
                    prof = {
                        "company_name": "高危注销空壳科技有限公司",
                        "regStatus": "已注销",
                        "establishTime": "2024-01-10",
                        "socialSecurityStaffNum": 0,
                        "失信被执行人": 2,
                    }
                else:
                    prof = {
                        "company_name": "星图国有控股集团股份有限公司",
                        "regStatus": "存续",
                        "establishTime": "2010-05-18",
                        "regCapital": "50000万人民币",
                        "socialSecurityStaffNum": 320,
                        "tags": ["国有企业", "上市公司"],
                        "失信被执行人": 0,
                    }
                return httpx.Response(
                    200,
                    headers={"content-type": "application/json"},
                    json={
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"structuredContent": prof, "content": []},
                    },
                )

        return httpx.Response(404, json={"error": "unknown method"})

    return httpx.MockTransport(handler)


def test_company_check_mcp_roundtrip_cache_and_severe_block(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("JOB_AUTO_ROOT", str(tmp_path))
    monkeypatch.setenv("TYC_MCP_API_KEY", "tyc-test-token-123")

    from job_agent.company_check import (
        filter_and_verify_prefilter_candidates,
        test_company_check_connection,
        verify_company_with_cache,
    )
    from job_agent.config import CompanyCheckConfig, UserConfig
    from job_agent.db import Database

    db = Database(tmp_path / "data" / "job_agent.db")
    db.init_schema()
    cfg = UserConfig(
        company_check=CompanyCheckConfig(
            enabled=True,
            provider="tianyancha_mcp",
            mcp_url="https://mcp.tianyancha.com/v1",
            api_key_env="TYC_MCP_API_KEY",
            cache_days=30,
            min_score_to_check=60,
            auto_reject_severe_risk=True,
        )
    )

    calls: list[str] = []
    transport = _build_mock_mcp_transport(calls)

    def _client_factory() -> httpx.Client:
        return httpx.Client(transport=transport)

    # 1. Connection & tools/list test
    conn_res = test_company_check_connection(cfg, root=tmp_path, client_factory=_client_factory)
    assert conn_res["status"] == "ok"
    assert conn_res["tool_count"] == 2
    assert "search_companies" in conn_res["sample_tools"]

    # 2. First verification hits MCP & persists to SQLite cache
    calls.clear()
    ok_res = verify_company_with_cache(
        db, cfg, "星图国有控股集团股份有限公司", root=tmp_path, client_factory=_client_factory
    )
    assert ok_res["risk_level"] == "pass"
    assert ok_res["reg_status"] == "存续"
    assert "320" in ok_res["risk_summary"]
    assert "国有企业" in ok_res["tags"]
    assert ok_res["cached"] is False
    assert "tool:search_companies" in calls
    assert "tool:get_company_basic_profile" in calls

    # 3. Second verification uses cache with ZERO HTTP calls
    calls.clear()
    cached_res = verify_company_with_cache(
        db, cfg, "星图国有控股集团股份有限公司", root=tmp_path, client_factory=_client_factory
    )
    assert cached_res["cached"] is True
    assert cached_res["risk_level"] == "pass"
    assert calls == []

    # 4. Stage 2 batch check blocks severe risk job BEFORE LLM tailoring while keeping pass & below-cutoff
    candidates_with_meta = [
        ({"id": 1, "company": "星图国有控股集团股份有限公司", "title": "会计"}, SimpleNamespace(rule_score_hint=80)),
        ({"id": 2, "company": "高危注销空壳科技有限公司", "title": "财务助理"}, SimpleNamespace(rule_score_hint=75)),
        ({"id": 3, "company": "低分未达触发线企业", "title": "出纳"}, SimpleNamespace(rule_score_hint=30)),
    ]
    kept, stats = filter_and_verify_prefilter_candidates(
        db, cfg, candidates_with_meta, root=tmp_path, client_factory=_client_factory
    )
    kept_ids = [int(j["id"]) for j in kept]
    assert kept_ids == [1, 3]
    assert stats["severe_blocked"] == 1
    assert stats["cached_hits"] == 1
    assert stats["checked_new"] == 1


def test_company_check_settings_api_and_workbench_integration(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("JOB_AUTO_ROOT", str(tmp_path))
    from fastapi.testclient import TestClient

    from job_agent.db import Database
    from job_agent.demo_seed import seed_demo_workspace
    from job_agent.stage3.review_server import create_review_app

    db_path = tmp_path / "data" / "job_agent.db"
    out_root = tmp_path / "output"
    db = Database(db_path)
    seed_demo_workspace(db, output_root=out_root)

    # Pre-seed a company check record for one demo company
    db.upsert_company_verification(
        {
            "company_key": "晋商银行示例企业",
            "company_name": "晋商银行（示例企业）",
            "matched_company_name": "晋商银行股份有限公司",
            "provider": "tianyancha_mcp",
            "reg_status": "存续",
            "risk_level": "pass",
            "risk_summary": "存续 · 2009年成立 · 参保2400人 · 工商核验正常",
            "tags": ["国有企业"],
            "raw": {},
            "source_tools": "search_companies, get_company_basic_profile",
        }
    )

    app = create_review_app(db_path=db_path, output_root=out_root)
    client = TestClient(app)

    # 1. Settings exposes company_check presets & persists secret into .env safely
    r_save = client.post(
        "/api/system/settings",
        json={
            "company_check": {
                "enabled": True,
                "provider": "tianyancha_mcp",
                "api_key_env": "TYC_MCP_API_KEY",
                "api_key": "tyc-secret-998877",
                "min_score_to_check": 65,
                "cache_days": 14,
                "auto_reject_severe_risk": True,
            }
        },
    )
    assert r_save.status_code == 200
    assert "TYC_MCP_API_KEY" in r_save.json()["updated_env_keys"]

    r_get = client.get("/api/system/settings").json()
    assert len(r_get["company_check_presets"]) >= 3
    cc = r_get["company_check"]
    assert cc["enabled"] is True
    assert cc["provider"] == "tianyancha_mcp"
    assert cc["api_key_set"] is True
    assert "998877" not in cc["api_key_masked"] or "*" in cc["api_key_masked"]
    assert cc["min_score_to_check"] == 65
    assert cc["cache_days"] == 14

    # 2. Packages & Data dashboard return company_check enrichment
    pkgs = client.get("/api/packages").json()["packages"]
    bank_pkg = next(p for p in pkgs if "晋商银行" in p["company"])
    assert bank_pkg["company_check"]["risk_level"] == "pass"
    assert "参保2400人" in bank_pkg["company_check"]["risk_summary"]

    dash = client.get("/api/data/jobs-dashboard").json()
    bank_job = next(j for j in dash["jobs"] if "晋商银行" in j["company"])
    assert bank_job["company_check"]["risk_level"] == "pass"

    # 3. HTML UI contains new Company Check controls
    html = client.get("/review").text
    assert "cfgCcEnabled" in html
    assert "btnSaveCompanyCheck" in html
    assert "btnTestCompanyCheck" in html
    assert "btnVerifyCompanyNow" in html
