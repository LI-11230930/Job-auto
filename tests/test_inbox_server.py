"""Tests for local companion extension inbox FastAPI server."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from job_agent.inbox_server import create_inbox_app


def test_inbox_health_and_ingest_page_stores_snapshot_and_jobs(tmp_path: Path) -> None:
    db_path = tmp_path / "job_agent.db"
    inbox_dir = tmp_path / "inbox"
    app = create_inbox_app(db_path=db_path, inbox_dir=inbox_dir, refresh_progress=False)
    client = TestClient(app)

    h = client.get("/api/health")
    assert h.status_code == 200
    assert h.json()["total_in_db"] == 0

    zhipin_html = """
    <html><body><ul>
      <li class="job-card-box">
        <a class="job-title" href="/job_detail/abc123.html">财务管培生（2027校招）</a>
        <span class="job-salary">6-8K</span>
        <a class="boss-name">太原晋阳医药有限公司</a>
        <span class="company-location">太原·小店区</span>
        <ul class="tag-list"><li>2027应届生</li><li>会计学</li></ul>
      </li>
    </ul></body></html>
    """
    resp = client.post(
        "/api/ingest-page",
        json={
            "url": "https://www.zhipin.com/web/geek/job?city=101100100&query=%E8%B4%A2%E5%8A%A1",
            "site": "auto",
            "html": zhipin_html,
            "cards": [
                {
                    "title": "会计助理（2027校招）",
                    "company": "山西华丰建工集团",
                    "city": "太原·迎泽区",
                    "salary": "5-7K",
                    "tags": ["校招", "用友U8"],
                    "url": "https://www.zhipin.com/job_detail/xyz999.html",
                }
            ],
            "exclude_social": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["site"] == "zhipin"
    assert body["extracted"] == 2
    assert body["inserted"] == 2
    assert body["total_in_db"] == 2
    assert Path(body["snapshot_path"]).exists()

    # Duplicate ingest updates without creating duplicate rows
    resp2 = client.post(
        "/api/ingest-page",
        json={
            "url": "https://www.zhipin.com/web/geek/job?page=1",
            "site": "zhipin",
            "html": zhipin_html,
            "cards": [],
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["inserted"] == 0
    assert resp2.json()["total_in_db"] == 2
