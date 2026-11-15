"""SQLite WAL-mode database initialization and repository layer."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS master_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_tag TEXT NOT NULL UNIQUE,
    profile_json TEXT NOT NULL,
    qa_bank_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_job_id TEXT NOT NULL DEFAULT '',
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    cities_json TEXT NOT NULL DEFAULT '[]',
    job_type TEXT NOT NULL DEFAULT '未知',
    jd_text TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    apply_channel TEXT NOT NULL DEFAULT 'unknown',
    apply_target TEXT NOT NULL DEFAULT '',
    deadline TEXT NOT NULL DEFAULT '',
    industry TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    dedup_hash TEXT NOT NULL UNIQUE,
    priority_rank INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    master_version_id INTEGER NOT NULL REFERENCES master_versions(id),
    rule_pass INTEGER NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    reasons_json TEXT NOT NULL DEFAULT '[]',
    gaps_json TEXT NOT NULL DEFAULT '[]',
    strategy_json TEXT NOT NULL DEFAULT '{}',
    model TEXT NOT NULL DEFAULT '',
    prompt_version TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    master_version_id INTEGER NOT NULL REFERENCES master_versions(id),
    resume_pdf_path TEXT NOT NULL DEFAULT '',
    diff_md_path TEXT NOT NULL DEFAULT '',
    qa_json TEXT NOT NULL DEFAULT '{}',
    greeting TEXT NOT NULL DEFAULT '',
    retry_count INTEGER NOT NULL DEFAULT 0,
    factcheck_status TEXT NOT NULL DEFAULT 'blocked',
    factcheck_log TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id INTEGER NOT NULL REFERENCES packages(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject', 'later')),
    reason TEXT NOT NULL DEFAULT '',
    decided_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    package_id INTEGER REFERENCES packages(id) ON DELETE SET NULL,
    channel TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('manual', 'assist', 'auto')),
    status TEXT NOT NULL DEFAULT '待提交',
    submitted_at TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_type TEXT NOT NULL,
    status TEXT NOT NULL,
    stats_json TEXT NOT NULL DEFAULT '{}',
    error_log TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS app_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'info',
    category TEXT NOT NULL DEFAULT 'daily_digest',
    action_tab TEXT NOT NULL DEFAULT 'detail',
    payload_json TEXT NOT NULL DEFAULT '{}',
    delivered_channels_json TEXT NOT NULL DEFAULT '[]',
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_app_notifications_unread ON app_notifications(is_read, id DESC);
"""


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def normalize_job_type_filter(job_type: str | None) -> str:
    """Normalize track filter aliases ('秋招'/'校招' -> '校招', '实习' -> '实习', else 'all')."""
    raw = (job_type or "").strip()
    if raw in {"秋招", "校招", "校园"}:
        return "校招"
    if raw == "实习":
        return "实习"
    return "all"


class Database:
    """Thin, deterministic SQLite wrapper for Job-auto."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)

    def init_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def start_run(self, run_type: str) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO runs (run_type, status, started_at) VALUES (?, 'running', ?)",
                (run_type, utc_now_iso()),
            )
            return int(cur.lastrowid)

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        stats: dict[str, Any],
        error_log: str = "",
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = ?, stats_json = ?, error_log = ?, finished_at = ?
                WHERE id = ?
                """,
                (status, json.dumps(stats, ensure_ascii=False), error_log, utc_now_iso(), run_id),
            )

    def upsert_jobs(self, jobs: list[dict[str, Any]]) -> dict[str, int]:
        """Insert new jobs or merge cities/upgrade apply_channel on dedup_hash collision."""
        inserted = 0
        updated = 0
        skipped = 0
        now = utc_now_iso()

        with self.connect() as conn:
            for item in jobs:
                dedup_hash = item["dedup_hash"]
                existing = conn.execute(
                    "SELECT id, cities_json, priority_rank, jd_text, deadline FROM jobs WHERE dedup_hash = ?",
                    (dedup_hash,),
                ).fetchone()

                new_cities = list(dict.fromkeys(item.get("cities") or []))
                if existing is None:
                    conn.execute(
                        """
                        INSERT INTO jobs (
                            source, source_job_id, company, title, cities_json, job_type,
                            jd_text, url, apply_channel, apply_target, deadline, industry,
                            status, dedup_hash, priority_rank, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item["source"],
                            item.get("source_job_id", ""),
                            item["company"],
                            item["title"],
                            json.dumps(new_cities, ensure_ascii=False),
                            item.get("job_type", "未知"),
                            item.get("jd_text", ""),
                            item.get("url", ""),
                            item.get("apply_channel", "unknown"),
                            item.get("apply_target", ""),
                            item.get("deadline", ""),
                            item.get("industry", ""),
                            item.get("status", "active"),
                            dedup_hash,
                            int(item.get("priority_rank", 0)),
                            now,
                            now,
                        ),
                    )
                    inserted += 1
                    continue

                old_cities = json.loads(existing["cities_json"])
                merged_cities = list(dict.fromkeys([*old_cities, *new_cities]))
                new_rank = int(item.get("priority_rank", 0))
                should_upgrade_channel = new_rank > int(existing["priority_rank"])
                has_richer_jd = len(item.get("jd_text", "")) > len(existing["jd_text"] or "")
                new_deadline = item.get("deadline") or existing["deadline"] or ""

                if (
                    merged_cities != old_cities
                    or should_upgrade_channel
                    or has_richer_jd
                    or (new_deadline != (existing["deadline"] or ""))
                ):
                    if should_upgrade_channel:
                        conn.execute(
                            """
                            UPDATE jobs
                            SET cities_json = ?, source = ?, source_job_id = ?, url = ?,
                                apply_channel = ?, apply_target = ?, priority_rank = ?,
                                jd_text = CASE WHEN length(?) > length(jd_text) THEN ? ELSE jd_text END,
                                deadline = ?, updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                json.dumps(merged_cities, ensure_ascii=False),
                                item["source"],
                                item.get("source_job_id", ""),
                                item.get("url", ""),
                                item.get("apply_channel", "unknown"),
                                item.get("apply_target", ""),
                                new_rank,
                                item.get("jd_text", ""),
                                item.get("jd_text", ""),
                                new_deadline,
                                now,
                                existing["id"],
                            ),
                        )
                    else:
                        conn.execute(
                            """
                            UPDATE jobs
                            SET cities_json = ?,
                                jd_text = CASE WHEN length(?) > length(jd_text) THEN ? ELSE jd_text END,
                                deadline = ?, updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                json.dumps(merged_cities, ensure_ascii=False),
                                item.get("jd_text", ""),
                                item.get("jd_text", ""),
                                new_deadline,
                                now,
                                existing["id"],
                            ),
                        )
                    updated += 1
                else:
                    skipped += 1

        return {"inserted": inserted, "updated": updated, "skipped": skipped}

    def count_jobs(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM jobs").fetchone()
            return int(row["cnt"])

    def upsert_master_version(
        self,
        *,
        version_tag: str,
        profile_json: str,
        qa_bank_json: str,
    ) -> int:
        now = utc_now_iso()
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM master_versions WHERE version_tag = ?",
                (version_tag,),
            ).fetchone()
            if existing is not None:
                conn.execute(
                    """
                    UPDATE master_versions
                    SET profile_json = ?, qa_bank_json = ?
                    WHERE id = ?
                    """,
                    (profile_json, qa_bank_json, existing["id"]),
                )
                return int(existing["id"])
            cur = conn.execute(
                """
                INSERT INTO master_versions (version_tag, profile_json, qa_bank_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (version_tag, profile_json, qa_bank_json, now),
            )
            return int(cur.lastrowid)

    def get_latest_master_version(self) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM master_versions ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row is not None else None

    def insert_match(
        self,
        *,
        job_id: int,
        master_version_id: int,
        rule_pass: bool,
        score: int,
        reasons: list[dict[str, Any]],
        gaps: list[str],
        strategy: dict[str, Any],
        model: str,
        prompt_version: str,
    ) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO matches (
                    job_id, master_version_id, rule_pass, score,
                    reasons_json, gaps_json, strategy_json, model, prompt_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    master_version_id,
                    1 if rule_pass else 0,
                    score,
                    json.dumps(reasons, ensure_ascii=False),
                    json.dumps(gaps, ensure_ascii=False),
                    json.dumps(strategy, ensure_ascii=False),
                    model,
                    prompt_version,
                    utc_now_iso(),
                ),
            )
            return int(cur.lastrowid)

    def insert_package(
        self,
        *,
        job_id: int,
        match_id: int,
        master_version_id: int,
        resume_pdf_path: str,
        diff_md_path: str,
        qa: dict[str, Any],
        greeting: str,
        retry_count: int,
        factcheck_status: str,
        factcheck_log: str = "",
    ) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO packages (
                    job_id, match_id, master_version_id, resume_pdf_path, diff_md_path,
                    qa_json, greeting, retry_count, factcheck_status, factcheck_log, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    match_id,
                    master_version_id,
                    resume_pdf_path,
                    diff_md_path,
                    json.dumps(qa, ensure_ascii=False),
                    greeting,
                    retry_count,
                    factcheck_status,
                    factcheck_log,
                    utc_now_iso(),
                ),
            )
            return int(cur.lastrowid)

    def get_matches_needing_packages(
        self,
        *,
        master_version_id: int,
        min_score: int,
        limit: int = 20,
    ) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT m.*, j.source AS j_source, j.company AS j_company, j.title AS j_title,
                       j.cities_json AS j_cities_json, j.job_type AS j_job_type,
                       j.jd_text AS j_jd_text, j.url AS j_url, j.apply_channel AS j_apply_channel
                FROM matches m
                JOIN jobs j ON j.id = m.job_id
                LEFT JOIN packages p ON p.match_id = m.id
                WHERE m.master_version_id = ?
                  AND m.rule_pass = 1
                  AND m.score >= ?
                  AND p.id IS NULL
                ORDER BY m.score DESC, m.id DESC
                LIMIT ?
                """,
                (master_version_id, min_score, limit),
            ).fetchall()
        results: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for row in rows:
            d = dict(row)
            job_dict = {
                "id": d["job_id"],
                "source": d.pop("j_source"),
                "company": d.pop("j_company"),
                "title": d.pop("j_title"),
                "cities_json": d.pop("j_cities_json"),
                "job_type": d.pop("j_job_type"),
                "jd_text": d.pop("j_jd_text"),
                "url": d.pop("j_url"),
                "apply_channel": d.pop("j_apply_channel"),
            }
            results.append((job_dict, d))
        return results

    def list_packages_for_review(
        self,
        *,
        decision_filter: str = "all",
        job_type_filter: str = "all",
        min_score: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List generated packages with job, match, latest decision, and application status."""
        norm_type = normalize_job_type_filter(job_type_filter)
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT p.id AS package_id,
                       p.job_id,
                       p.match_id,
                       p.resume_pdf_path,
                       p.diff_md_path,
                       p.qa_json,
                       p.greeting,
                       p.retry_count,
                       p.factcheck_status,
                       p.created_at AS package_created_at,
                       m.score,
                       m.reasons_json,
                       m.gaps_json,
                       m.strategy_json,
                       m.model,
                       j.source,
                       j.company,
                       j.title,
                       j.cities_json,
                       j.job_type,
                       j.deadline,
                       j.url,
                       j.apply_channel,
                       j.status AS job_status,
                       j.jd_text,
                       COALESCE(
                           (SELECT d.decision FROM decisions d
                            WHERE d.package_id = p.id
                            ORDER BY d.id DESC LIMIT 1),
                           'pending'
                       ) AS decision,
                       COALESCE(
                           (SELECT d.reason FROM decisions d
                            WHERE d.package_id = p.id
                            ORDER BY d.id DESC LIMIT 1),
                           ''
                       ) AS decision_reason,
                       COALESCE(
                           (SELECT a.status FROM applications a
                            WHERE a.package_id = p.id
                            ORDER BY a.id DESC LIMIT 1),
                           ''
                       ) AS application_status
                FROM packages p
                JOIN matches m ON m.id = p.match_id
                JOIN jobs j ON j.id = p.job_id
                WHERE m.score >= ?
                ORDER BY m.score DESC, p.id DESC
                LIMIT ?
                """,
                (
                    min_score,
                    limit * 5 if (decision_filter != "all" or norm_type != "all") else limit,
                ),
            ).fetchall()

        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            if item.get("job_status") == "restricted_campus" and item["decision"] == "pending":
                continue
            if decision_filter != "all" and item["decision"] != decision_filter:
                continue
            if norm_type != "all" and item.get("job_type") != norm_type:
                continue
            for col in ("cities_json", "reasons_json", "gaps_json", "strategy_json", "qa_json"):
                key = col.removesuffix("_json")
                try:
                    item[key] = json.loads(item.get(col) or ("{}" if col in ("strategy_json", "qa_json") else "[]"))
                except json.JSONDecodeError:
                    item[key] = {} if col in ("strategy_json", "qa_json") else []
            out.append(item)
            if len(out) >= limit:
                break
        return out

    def get_package_detail(self, package_id: int) -> dict[str, Any] | None:
        """Fetch full package details including diff.md text if present on disk."""
        rows = self.list_packages_for_review(decision_filter="all", min_score=0, limit=500)
        for item in rows:
            if int(item["package_id"]) == int(package_id):
                diff_text = ""
                diff_p = Path(item.get("diff_md_path") or "")
                if diff_p.is_file():
                    diff_text = diff_p.read_text(encoding="utf-8", errors="replace")
                item["diff_md_text"] = diff_text
                pdf_p = Path(item.get("resume_pdf_path") or "")
                item["pdf_exists"] = pdf_p.is_file()
                return item
        return None

    def record_decision(
        self,
        *,
        package_id: int,
        decision: str,
        reason: str = "",
        default_mode: str = "assist",
    ) -> dict[str, Any]:
        """Record human decision ('approve'|'reject'|'later') and enqueue approved jobs."""
        if decision not in {"approve", "reject", "later"}:
            raise ValueError(f"Invalid decision: {decision}")
        now = utc_now_iso()
        with self.connect() as conn:
            pkg = conn.execute(
                """
                SELECT p.id, p.job_id, j.apply_channel
                FROM packages p
                JOIN jobs j ON j.id = p.job_id
                WHERE p.id = ?
                """,
                (package_id,),
            ).fetchone()
            if pkg is None:
                raise LookupError(f"Package not found: {package_id}")

            cur = conn.execute(
                """
                INSERT INTO decisions (package_id, job_id, decision, reason, decided_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (package_id, int(pkg["job_id"]), decision, reason, now),
            )
            decision_id = int(cur.lastrowid)
            application_id = None
            if decision == "approve":
                existing_app = conn.execute(
                    "SELECT id FROM applications WHERE package_id = ? ORDER BY id DESC LIMIT 1",
                    (package_id,),
                ).fetchone()
                if existing_app is not None:
                    application_id = int(existing_app["id"])
                else:
                    mode = default_mode if default_mode in {"manual", "assist", "auto"} else "assist"
                    app_cur = conn.execute(
                        """
                        INSERT INTO applications (
                            job_id, package_id, channel, mode, status, submitted_at, notes, updated_at
                        ) VALUES (?, ?, ?, ?, '待提交', '', ?, ?)
                        """,
                        (
                            int(pkg["job_id"]),
                            package_id,
                            str(pkg["apply_channel"] or "unknown"),
                            mode,
                            reason,
                            now,
                        ),
                    )
                    application_id = int(app_cur.lastrowid)
        return {
            "decision_id": decision_id,
            "package_id": package_id,
            "job_id": int(pkg["job_id"]),
            "decision": decision,
            "application_id": application_id,
        }

    def list_applications(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """List Stage 3/4 delivery queue rows joined with job and package paths."""
        sql = """
            SELECT a.*, j.company, j.title, j.cities_json, j.job_type, j.url, j.source,
                   j.apply_channel, j.apply_target, j.deadline, j.jd_text,
                   p.resume_pdf_path, p.greeting, p.qa_json, m.score
            FROM applications a
            JOIN jobs j ON j.id = a.job_id
            LEFT JOIN packages p ON p.id = a.package_id
            LEFT JOIN matches m ON m.id = p.match_id
        """
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("a.status = ?")
            params.append(status)
        norm_type = normalize_job_type_filter(job_type)
        if norm_type != "all":
            clauses.append("j.job_type = ?")
            params.append(norm_type)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY a.id DESC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            try:
                item["cities"] = json.loads(item.get("cities_json") or "[]")
            except json.JSONDecodeError:
                item["cities"] = []
            try:
                qa_raw = json.loads(item.get("qa_json") or "{}")
                item["qa"] = qa_raw if isinstance(qa_raw, dict) else {}
            except json.JSONDecodeError:
                item["qa"] = {}
            out.append(item)
        return out

    def enrich_job_delivery_details(
        self,
        *,
        job_id: int,
        jd_text: str | None = None,
        apply_channel: str | None = None,
        apply_target: str | None = None,
    ) -> None:
        """Persist enriched JD details or upgraded apply target onto jobs row."""
        now = utc_now_iso()
        updates: list[str] = ["updated_at = ?"]
        params: list[Any] = [now]
        if jd_text is not None:
            updates.append("jd_text = ?")
            params.append(jd_text)
        if apply_channel:
            updates.append("apply_channel = ?")
            params.append(apply_channel)
        if apply_target:
            updates.append("apply_target = ?")
            params.append(apply_target)
        params.append(job_id)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?",
                params,
            )

    def update_application_status(
        self,
        *,
        application_id: int,
        status: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Update submission tracking status and record timestamp when submitted."""
        now = utc_now_iso()
        submitted_at = now if status == "已投递" else ""
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT id, submitted_at, notes FROM applications WHERE id = ?",
                (application_id,),
            ).fetchone()
            if existing is None:
                raise LookupError(f"Application not found: {application_id}")
            keep_submitted = existing["submitted_at"] or submitted_at
            keep_notes = existing["notes"] if notes is None else notes
            conn.execute(
                """
                UPDATE applications
                SET status = ?, notes = ?, submitted_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, keep_notes, keep_submitted, now, application_id),
            )
        return {
            "application_id": application_id,
            "status": status,
            "notes": keep_notes,
            "updated_at": now,
        }

    def add_notification(
        self,
        *,
        title: str,
        body: str,
        level: str = "info",
        category: str = "daily_digest",
        action_tab: str = "detail",
        payload: dict[str, Any] | None = None,
        delivered_channels: list[str] | None = None,
    ) -> int:
        """Persist an in-app / desktop notification event for the standalone App inbox."""
        now = utc_now_iso()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO app_notifications (
                    title, body, level, category, action_tab,
                    payload_json, delivered_channels_json, is_read, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    title.strip()[:200],
                    body.strip()[:2000],
                    level.strip() or "info",
                    category.strip() or "daily_digest",
                    action_tab.strip() or "detail",
                    json.dumps(payload or {}, ensure_ascii=False),
                    json.dumps(delivered_channels or [], ensure_ascii=False),
                    now,
                ),
            )
            assert cur.lastrowid is not None
            return int(cur.lastrowid)

    def update_notification_channels(self, notification_id: int, channels: list[str]) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE app_notifications SET delivered_channels_json = ? WHERE id = ?",
                (json.dumps(channels, ensure_ascii=False), notification_id),
            )

    def count_unread_notifications(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM app_notifications WHERE is_read = 0").fetchone()
            return int(row[0]) if row else 0

    def list_notifications(
        self,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        where = "WHERE is_read = 0" if unread_only else ""
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, title, body, level, category, action_tab,
                       payload_json, delivered_channels_json, is_read, created_at
                FROM app_notifications
                {where}
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            item = dict(r)
            try:
                item["payload"] = json.loads(item.pop("payload_json", "{}") or "{}")
            except json.JSONDecodeError:
                item["payload"] = {}
            try:
                item["delivered_channels"] = json.loads(item.pop("delivered_channels_json", "[]") or "[]")
            except json.JSONDecodeError:
                item["delivered_channels"] = []
            item["is_read"] = bool(item.get("is_read"))
            out.append(item)
        return out

    def mark_notifications_read(self, notification_ids: list[int] | None = None) -> int:
        with self.connect() as conn:
            if notification_ids:
                clean_ids = [int(x) for x in notification_ids]
                placeholders = ",".join("?" for _ in clean_ids)
                cur = conn.execute(
                    f"UPDATE app_notifications SET is_read = 1 WHERE id IN ({placeholders}) AND is_read = 0",
                    clean_ids,
                )
            else:
                cur = conn.execute("UPDATE app_notifications SET is_read = 1 WHERE is_read = 0")
            return int(cur.rowcount or 0)
