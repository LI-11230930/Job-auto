"""Stage 2.5: Rich single-page A4 resume HTML -> PDF renderer modeled on the user's HTML template."""

from __future__ import annotations

import base64
import html
import json
import mimetypes
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from ..master import MasterBullet, MasterExperience, MasterProfile

# 297mm at 96 DPI ~= 1122.5px; allow 1118px budget inside .resume-page so zero clipping occurs.
_A4_MAX_SCROLL_HEIGHT_PX = 1118

_SVG_PHONE = (
    '<svg viewBox="0 0 24 24"><path d="M6.62 10.79a15.05 15.05 0 006.59 6.59l2.2-2.2a1 1 0 '
    '011.02-.24 11.72 11.72 0 003.68.59 1 1 0 011 1V20a1 1 0 01-1 1A17 17 0 013 4a1 1 0 011-1h3.5'
    'a1 1 0 011 1 11.72 11.72 0 00.59 3.68 1 1 0 01-.24 1.02l-2.23 2.09z"/></svg>'
)
_SVG_EMAIL = (
    '<svg viewBox="0 0 24 24"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 '
    '2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>'
)
_SVG_LOC = (
    '<svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13'
    'c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5z"/></svg>'
)
_SVG_GRAD = (
    '<svg viewBox="0 0 24 24"><path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19a2 2 '
    '0 002 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z"/></svg>'
)
_SVG_CERT = (
    '<svg viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 '
    '9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/></svg>'
)
_SVG_CHECK = (
    '<svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>'
)
_SVG_LINK = (
    '<svg viewBox="0 0 24 24"><path d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 '
    '5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 '
    '1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z"/></svg>'
)

_HIGHLIGHT_TOOL_PATTERNS = [
    "金蝶EAS",
    "金蝶云",
    "用友U8",
    "用友 U8",
    "畅捷通T+",
    "畅捷通 T+",
    "审计大师多年版",
    "Laiye RPA",
    "Python",
    "Pandas",
    "XLOOKUP",
    "VLOOKUP",
    "Excel",
    "杜邦分析",
]


def _encode_avatar_data_uri(image_path: Path | None) -> str:
    if image_path is None or not image_path.exists() or not image_path.is_file():
        return ""
    mime, _ = mimetypes.guess_type(str(image_path))
    mime_type = mime or "image/png"
    b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def load_safe_display_contact(
    vault_dir: Path | None,
    *,
    fallback_resume_dir: Path | None = None,
) -> dict[str, str]:
    """Load ONLY display-safe header contact fields & photo locally (never sent to LLM)."""
    defaults = {
        "name": "求职者（示例档案）",
        "phone": "",
        "email": "",
        "city_intent": "",
        "demo_url": "",
        "political_status": "",
        "avatar_data_uri": "",
    }
    avatar_uri = ""
    search_dirs = [d for d in (vault_dir, fallback_resume_dir) if d is not None]
    for folder in search_dirs:
        for fname in ("avatar.png", "avatar.jpg", "avatar.jpeg", "photo.png", "photo.jpg"):
            cand = folder / fname
            if cand.exists():
                avatar_uri = _encode_avatar_data_uri(cand)
                break
        if avatar_uri:
            break

    if vault_dir is None:
        return {**defaults, "avatar_data_uri": avatar_uri}
    secrets_path = vault_dir / "personal_secrets.json"
    if not secrets_path.exists():
        return {**defaults, "avatar_data_uri": avatar_uri}
    try:
        raw = json.loads(secrets_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {**defaults, "avatar_data_uri": avatar_uri}
        return {
            "name": str(raw.get("full_name") or raw.get("name") or defaults["name"]).strip(),
            "phone": str(raw.get("phone") or "").strip(),
            "email": str(
                raw.get("email") or raw.get("email_notify") or raw.get("email_primary") or ""
            ).strip(),
            "city_intent": str(raw.get("city_intent") or defaults["city_intent"]).strip(),
            "hometown": str(raw.get("hometown") or "").strip(),
            "demo_url": str(raw.get("demo_url") or defaults["demo_url"]).strip(),
            "political_status": str(raw.get("political_status") or "").strip(),
            "avatar_data_uri": avatar_uri,
        }
    except (OSError, json.JSONDecodeError):
        return {**defaults, "avatar_data_uri": avatar_uri}


def should_include_demo_url(job: dict[str, Any]) -> bool:
    """Keep personal live demo link for digital/ERP/data roles; omit for conservative SOE accounting."""
    text = f"{job.get('title', '')} {job.get('jd_text', '')}".lower()
    tech_hints = (
        "erp",
        "用友",
        "金蝶",
        "畅捷通",
        "数智",
        "信息化",
        "数字化",
        "实施",
        "python",
        "sql",
        "系统",
        "数据分析",
    )
    return any(k in text for k in tech_hints)


def _group_tailored_experiences(
    profile: MasterProfile,
    selected: list[dict[str, str]],
) -> list[tuple[MasterExperience, list[tuple[MasterBullet, str]]]]:
    bullet_lookup: dict[str, tuple[MasterExperience, MasterBullet]] = {}
    for exp in profile.experiences:
        for b in exp.bullets:
            bullet_lookup[b.id] = (exp, b)

    grouped: dict[str, list[tuple[MasterBullet, str]]] = {}
    exp_order: dict[str, MasterExperience] = {}
    for item in selected:
        bid = str(item.get("id") or "").strip()
        text = str(item.get("rewritten") or "").strip()
        if bid not in bullet_lookup or not text:
            continue
        exp, orig_b = bullet_lookup[bid]
        exp_order[exp.id] = exp
        grouped.setdefault(exp.id, []).append((orig_b, text))

    ordered_ids = [e.id for e in profile.experiences if e.id in grouped]
    return [(exp_order[eid], grouped[eid]) for eid in ordered_ids]


def _format_bullet_html(text: str) -> str:
    """Format bullet with bold 【topic】 prefix and key ERP/tool emphasis without changing wording."""
    esc = html.escape
    stripped = text.strip()
    prefix_html = ""
    rest = stripped
    m = re.match(r"^(【[^】]{2,20}】)\s*(.*)$", stripped)
    if m:
        prefix_html = f"<strong>{esc(m.group(1))}</strong> "
        rest = m.group(2)

    # Bold allowed tool names safely via placeholder tokens after escaping
    body_esc = esc(rest)
    for idx, tok in enumerate(_HIGHLIGHT_TOOL_PATTERNS):
        if tok in body_esc:
            body_esc = body_esc.replace(tok, f"@@B{idx}@@")
    for idx, tok in enumerate(_HIGHLIGHT_TOOL_PATTERNS):
        placeholder = f"@@B{idx}@@"
        if placeholder in body_esc:
            body_esc = body_esc.replace(placeholder, f"<strong>{tok}</strong>")
    return f"{prefix_html}{body_esc}"


def _build_tag_pills(profile: MasterProfile, contact: dict[str, str]) -> list[tuple[str, bool]]:
    """Build 4-5 factual highlight/secondary pills strictly from MasterProfile + display contact."""
    pills: list[tuple[str, bool]] = []
    certs_joined = " ".join(profile.certifications)
    if "初级会计" in certs_joined:
        pills.append(("初级会计师职称资格", True))
    if contact.get("city_intent"):
        pills.append((f"意向区域：{contact['city_intent']}", True))
    pills.append((f"{profile.education.graduation_year}届{profile.education.major}本科", False))

    erp_names = [s.name for s in profile.skills if "erp" in s.category.lower()]
    if erp_names:
        pills.append((f"熟练 {' / '.join(erp_names[:3])}", False))

    data_names = [
        s.name.split("（")[0].strip()
        for s in profile.skills
        if any(k in s.name for k in ("Excel", "Python"))
    ]
    if data_names:
        pills.append((f"{' / '.join(data_names[:2])} 数据处理", False))

    if "C1驾驶证" in certs_joined and len(pills) < 6:
        pills.append(("C1驾驶证", False))
    return pills[:5]


def _build_skills_rows(
    profile: MasterProfile,
    contact: dict[str, str],
) -> list[tuple[str, str]]:
    """Assemble factual rows for .skills-box directly from MasterProfile."""
    esc = html.escape
    erp_items = [
        s
        for s in profile.skills
        if any(k in (s.category + s.name).lower() for k in ("erp", "审计", "用友", "金蝶", "畅捷通"))
    ]
    data_items = [s for s in profile.skills if s not in erp_items]

    rows: list[tuple[str, str]] = []
    if erp_items:
        formatted = "、".join(f"<strong>{esc(s.name)}</strong>（{esc(s.level)}）" for s in erp_items)
        rows.append(
            (
                "财税与ERP系统：",
                f"掌握{profile.education.major}专业核心课程与企业会计准则基础；实务工具方面涵盖 {formatted}，可完成账套初始化、凭证审核、资产台账核对与审计测试。",
            )
        )
    if data_items:
        formatted = "、".join(f"<strong>{esc(s.name)}</strong>（{esc(s.level)}）" for s in data_items)
        rows.append(
            (
                "办公与数智工具：",
                f"具备财会数据处理与办公自动化能力，工具能力包括 {formatted}，可用于跨表勾稽校验、数据清洗聚合与财务指标汇总。",
            )
        )

    qual_parts: list[str] = []
    if profile.certifications:
        certs = "、".join(esc(c) for c in profile.certifications)
        qual_parts.append(f"持有 {certs}")
    if contact.get("political_status"):
        qual_parts.append(f"政治面貌：{esc(contact['political_status'])}")
    qual_parts.append("工作作风严谨细致，注重账实核验与档案规范，期望长期稳定深耕财务条线")
    rows.append(("资质与综合素养：", "；".join(qual_parts) + "。"))
    return rows


def _render_exp_item_html(
    exp: MasterExperience,
    bullets: list[tuple[MasterBullet, str]],
    *,
    show_demo_link: bool,
    demo_url: str,
) -> str:
    esc = html.escape
    link_html = ""
    if exp.category == "project" and show_demo_link and demo_url:
        href = esc(demo_url if demo_url.startswith("http") else f"http://{demo_url}")
        link_html = (
            f'<a href="{href}" target="_blank" class="proj-link">'
            f"{_SVG_LINK} 在线系统：{esc(demo_url)}</a>"
        )
    lis = "".join(f"<li>{_format_bullet_html(text)}</li>" for _, text in bullets)
    return f"""
    <div class="exp-item">
      <div class="exp-header">
        <div class="exp-title-group">
          <span class="exp-org">{esc(exp.organization)}</span>
          <span class="exp-role">{esc(exp.role)}</span>
          {link_html}
        </div>
        <span class="exp-date">{esc(exp.period)}</span>
      </div>
      <ul class="bullet-list">{lis}</ul>
    </div>
    """


def render_resume_html(
    *,
    profile: MasterProfile,
    tailored: dict[str, Any],
    job: dict[str, Any],
    contact: dict[str, str] | None = None,
    compact_level: int = 0,
    intern_availability: str = "",
) -> str:
    """Build single-page A4 HTML faithfully modeled on user's navy-blue resume template."""
    c = contact or load_safe_display_contact(None)
    esc = html.escape
    selected = list(tailored.get("selected") or [])
    groups = _group_tailored_experiences(profile, selected)
    show_demo = should_include_demo_url(job)
    demo_url = c.get("demo_url", "")

    # Density tuning across 3 levels (0=standard, 1=tight, 2=ultra-compact) for 8-10 rich bullets
    metrics = {
        0: {
            "page_pad": "11.5mm 14mm 10mm 14mm",
            "top_h": "4.5mm",
            "name_px": "26px",
            "body_lh": "1.48",
            "sec_mb": "3.2mm",
            "exp_mb": "2.4mm",
            "bullet_px": "10.9px",
            "bullet_mb": "1.1mm",
            "photo_w": "82px",
            "photo_h": "110px",
            "skills_pad": "2.4mm 3.4mm",
        },
        1: {
            "page_pad": "9.5mm 13mm 8.5mm 13mm",
            "top_h": "4mm",
            "name_px": "24px",
            "body_lh": "1.41",
            "sec_mb": "2.4mm",
            "exp_mb": "1.8mm",
            "bullet_px": "10.4px",
            "bullet_mb": "0.85mm",
            "photo_w": "74px",
            "photo_h": "99px",
            "skills_pad": "2mm 3mm",
        },
        2: {
            "page_pad": "8mm 12mm 7mm 12mm",
            "top_h": "3.5mm",
            "name_px": "22px",
            "body_lh": "1.34",
            "sec_mb": "1.8mm",
            "exp_mb": "1.4mm",
            "bullet_px": "9.8px",
            "bullet_mb": "0.6mm",
            "photo_w": "68px",
            "photo_h": "91px",
            "skills_pad": "1.6mm 2.8mm",
        },
    }.get(compact_level, None) or {
        "page_pad": "8mm 12mm 7mm 12mm",
        "top_h": "3.5mm",
        "name_px": "22px",
        "body_lh": "1.34",
        "sec_mb": "1.8mm",
        "exp_mb": "1.4mm",
        "bullet_px": "9.8px",
        "bullet_mb": "0.6mm",
        "photo_w": "68px",
        "photo_h": "91px",
        "skills_pad": "1.6mm 2.8mm",
    }

    job_title = str(job.get("title") or "财务管培生")
    company = str(job.get("company") or "").strip()
    company_span = f" <span>（{esc(company)}）</span>" if company else ""

    pills_html = "".join(
        f'<span class="tag-pill{" highlight" if hi else ""}">{esc(label)}</span>'
        for label, hi in _build_tag_pills(profile, c)
    )

    edu = profile.education
    contact_items: list[str] = []
    if c.get("phone"):
        contact_items.append(
            f'<div class="contact-item">{_SVG_PHONE}<span><strong>{esc(c["phone"])}</strong></span></div>'
        )
    if c.get("email"):
        contact_items.append(
            f'<div class="contact-item">{_SVG_EMAIL}<span>{esc(c["email"])}</span></div>'
        )
    if c.get("city_intent"):
        contact_items.append(
            f'<div class="contact-item">{_SVG_LOC}<span>{esc(c["city_intent"])}</span></div>'
        )
    if c.get("political_status"):
        contact_items.append(
            f'<div class="contact-item">{_SVG_CERT}<span>政治面貌：{esc(c["political_status"])}</span></div>'
        )
    contact_items.append(
        f'<div class="contact-item">{_SVG_GRAD}<span>{edu.graduation_year}届本科学历（{esc(edu.period)}）</span></div>'
    )
    if job.get("job_type") == "实习" and intern_availability:
        contact_items.append(
            f'<div class="contact-item">{_SVG_CHECK}<span>{esc(intern_availability)}</span></div>'
        )
    elif show_demo and demo_url:
        contact_items.append(
            f'<div class="contact-item">{_SVG_LINK}<span>项目演示：{esc(demo_url)}</span></div>'
        )

    avatar_uri = c.get("avatar_data_uri", "")
    photo_html = (
        f'<div class="header-right"><div class="photo-frame"><img src="{avatar_uri}" alt="证件照"></div></div>'
        if avatar_uri
        else ""
    )

    edu_courses = "、".join(edu.core_courses[:8])
    certs_formatted = "｜".join(
        f"<strong>{esc(cert)}</strong>" if "初级会计" in cert else esc(cert)
        for cert in profile.certifications
    )

    intern_blocks = [
        _render_exp_item_html(exp, bullets, show_demo_link=show_demo, demo_url=demo_url)
        for exp, bullets in groups
        if exp.category == "internship"
    ]
    proj_blocks = [
        _render_exp_item_html(exp, bullets, show_demo_link=show_demo, demo_url=demo_url)
        for exp, bullets in groups
        if exp.category != "internship"
    ]

    intern_section_html = (
        f"""
        <div class="section">
          <div class="section-title-wrap">
            <div class="section-title"><span class="bar"></span><span>实习经历</span></div>
            <span class="section-subtitle">Internship Experience</span>
          </div>
          {"".join(intern_blocks)}
        </div>
        """
        if intern_blocks
        else ""
    )
    proj_section_html = (
        f"""
        <div class="section">
          <div class="section-title-wrap">
            <div class="section-title"><span class="bar"></span><span>项目与实训经历</span></div>
            <span class="section-subtitle">Project &amp; Practical Training</span>
          </div>
          {"".join(proj_blocks)}
        </div>
        """
        if proj_blocks
        else ""
    )

    skills_rows_html = "".join(
        f'<div class="skill-line"><span class="skill-label">{esc(lbl)}</span><span class="skill-desc">{desc}</span></div>'
        for lbl, desc in _build_skills_rows(profile, c)
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{esc(c['name'])} - {esc(job_title)} - 个人简历</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 0;
  }}
  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    color: #2d3748;
    background: #ffffff;
    line-height: {metrics['body_lh']};
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  .resume-page {{
    width: 210mm;
    min-height: 295mm;
    padding: {metrics['page_pad']};
    margin: 0 auto;
    position: relative;
    background: #ffffff;
  }}
  .top-stripe {{
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: {metrics['top_h']};
    background: linear-gradient(90deg, #0d233a 0%, #1a365d 45%, #2b6cb0 100%);
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding-bottom: 3mm;
    border-bottom: 1.5px solid #e2e8f0;
    margin-bottom: {metrics['sec_mb']};
  }}
  .header-left {{
    flex: 1;
    padding-right: 5mm;
  }}
  .name-row {{
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 2mm;
  }}
  .candidate-name {{
    font-size: {metrics['name_px']};
    font-weight: 800;
    color: #0d233a;
    letter-spacing: 2.2px;
    line-height: 1.15;
  }}
  .job-intent-badge {{
    display: inline-flex;
    align-items: center;
    background: #ebf4ff;
    color: #1a365d;
    font-size: 12px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 4px;
    border: 1px solid #bfdbfe;
    letter-spacing: 0.4px;
  }}
  .job-intent-badge span {{
    color: #2b6cb0;
    margin-left: 3px;
    font-weight: 600;
  }}
  .tag-pills {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 2.3mm;
  }}
  .tag-pill {{
    font-size: 10.5px;
    font-weight: 600;
    color: #2b6cb0;
    background: #f7fafc;
    border: 1px solid #cbd5e0;
    padding: 1.5px 7px;
    border-radius: 3px;
  }}
  .tag-pill.highlight {{
    background: #eff6ff;
    border-color: #93c5fd;
    color: #1d4ed8;
  }}
  .contact-grid {{
    display: grid;
    grid-template-columns: repeat(3, auto);
    gap: 5px 14px;
    font-size: 11px;
    color: #4a5568;
    margin-top: 1mm;
  }}
  .contact-item {{
    display: flex;
    align-items: center;
    gap: 5px;
  }}
  .contact-item svg {{
    width: 12.5px;
    height: 12.5px;
    fill: #2b6cb0;
    flex-shrink: 0;
  }}
  .header-right {{
    flex-shrink: 0;
  }}
  .photo-frame {{
    width: {metrics['photo_w']};
    height: {metrics['photo_h']};
    border-radius: 4px;
    border: 1.5px solid #cbd5e0;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
    overflow: hidden;
    background: #f8fafc;
  }}
  .photo-frame img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }}
  .section {{
    margin-bottom: {metrics['sec_mb']};
  }}
  .section-title-wrap {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 1.3mm;
    border-bottom: 1.5px solid #cbd5e0;
    margin-bottom: 2mm;
    position: relative;
  }}
  .section-title-wrap::after {{
    content: "";
    position: absolute;
    bottom: -1.5px;
    left: 0;
    width: 52px;
    height: 2px;
    background: #1a365d;
  }}
  .section-title {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13.5px;
    font-weight: 800;
    color: #0d233a;
    letter-spacing: 0.7px;
  }}
  .section-title .bar {{
    width: 4px;
    height: 13.5px;
    background: #1a365d;
    border-radius: 2px;
  }}
  .section-subtitle {{
    font-size: 9.5px;
    font-weight: 700;
    color: #a0aec0;
    letter-spacing: 1px;
    text-transform: uppercase;
  }}
    .edu-row {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 6px;
      font-size: 11.4px;
      font-weight: 700;
      color: #1a202c;
      margin-bottom: 1.2mm;
      white-space: nowrap;
    }}
    .edu-school {{
      color: #0d233a;
      font-size: 12.2px;
    }}
  .edu-major {{
    color: #2b6cb0;
  }}
  .edu-time {{
    color: #718096;
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
  }}
  .edu-details {{
    font-size: 10.9px;
    color: #4a5568;
    line-height: 1.5;
  }}
  .edu-details p {{
    margin-bottom: 0.6mm;
  }}
  .edu-details p:last-child {{
    margin-bottom: 0;
  }}
  .edu-details span.label {{
    font-weight: 700;
    color: #2d3748;
  }}
  .exp-item {{
    margin-bottom: {metrics['exp_mb']};
  }}
  .exp-item:last-child {{
    margin-bottom: 0;
  }}
  .exp-header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 1.1mm;
  }}
  .exp-title-group {{
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 7px;
  }}
  .exp-org {{
    font-size: 12.6px;
    font-weight: 800;
    color: #0d233a;
  }}
  .exp-role {{
    font-size: 11px;
    font-weight: 700;
    color: #2b6cb0;
    background: #edf2f7;
    padding: 1px 6.5px;
    border-radius: 3px;
  }}
  .exp-date {{
    font-size: 10.8px;
    font-weight: 600;
    color: #718096;
    white-space: nowrap;
  }}
  .proj-link {{
    font-size: 10.2px;
    font-weight: 600;
    color: #1d4ed8;
    text-decoration: none;
    padding: 0 5px;
    background: #eff6ff;
    border-radius: 3px;
    border: 1px solid #bfdbfe;
    display: inline-flex;
    align-items: center;
    gap: 3px;
  }}
  .proj-link svg {{
    width: 10px;
    height: 10px;
    fill: #2563eb;
  }}
  .bullet-list {{
    list-style: none;
    font-size: {metrics['bullet_px']};
    color: #374151;
    line-height: {metrics['body_lh']};
  }}
  .bullet-list li {{
    position: relative;
    padding-left: 11px;
    margin-bottom: {metrics['bullet_mb']};
    text-align: justify;
  }}
  .bullet-list li:last-child {{
    margin-bottom: 0;
  }}
  .bullet-list li::before {{
    content: "▪";
    position: absolute;
    left: 0;
    top: -0.5px;
    color: #2b6cb0;
    font-size: 11px;
  }}
  .bullet-list strong {{
    color: #0d233a;
    font-weight: 700;
  }}
  .skills-box {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: {metrics['skills_pad']};
  }}
  .skill-line {{
    font-size: {metrics['bullet_px']};
    color: #374151;
    line-height: 1.48;
    margin-bottom: 1mm;
    display: flex;
  }}
  .skill-line:last-child {{
    margin-bottom: 0;
  }}
  .skill-label {{
    font-weight: 800;
    color: #0d233a;
    width: 104px;
    flex-shrink: 0;
  }}
  .skill-desc {{
    flex: 1;
  }}
  .skill-desc strong {{
    color: #1a365d;
  }}
</style>
</head>
<body>
<div class="resume-page">
  <div class="top-stripe"></div>

  <div class="header">
    <div class="header-left">
      <div class="name-row">
        <h1 class="candidate-name">{esc(c['name'])}</h1>
        <div class="job-intent-badge">求职意向：{esc(job_title)}{company_span}</div>
      </div>
      <div class="tag-pills">{pills_html}</div>
      <div class="contact-grid">{"".join(contact_items)}</div>
    </div>
    {photo_html}
  </div>

  <div class="section">
    <div class="section-title-wrap">
      <div class="section-title"><span class="bar"></span><span>教育背景</span></div>
      <span class="section-subtitle">Education Background</span>
    </div>
    <div class="edu-row">
      <span class="edu-school">{esc(edu.school)}（{esc(edu.college.replace('（', ' / ').replace('）', ''))}）</span>
      <span class="edu-major">{esc(edu.major)}（{esc(edu.degree.replace('（', ' / ').replace('）', ''))}）</span>
      <span class="edu-time">{esc(edu.period)}（预计毕业）</span>
    </div>
    <div class="edu-details">
      {f'<p><span class="label">专业资格证书：</span>{certs_formatted}</p>' if certs_formatted else ''}
      {f'<p><span class="label">主修核心课程：</span>{esc(edu_courses)}</p>' if edu_courses else ''}
    </div>
  </div>

  {intern_section_html}
  {proj_section_html}

  <div class="section" style="margin-bottom: 0;">
    <div class="section-title-wrap">
      <div class="section-title"><span class="bar"></span><span>专业技能与综合素养</span></div>
      <span class="section-subtitle">Skills &amp; Competencies</span>
    </div>
    <div class="skills-box">{skills_rows_html}</div>
  </div>
</div>
</body>
</html>
"""


def _html_to_pdf_bytes_and_height(html_text: str) -> tuple[bytes, float]:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="msedge", headless=True)
        except PlaywrightError:
            browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 794, "height": 1123})
        page.set_content(html_text, wait_until="load")
        scroll_height = float(
            page.evaluate(
                "() => (document.querySelector('.resume-page') || document.body).scrollHeight"
            )
        )
        pdf_bytes = page.pdf(format="A4", print_background=True)
        browser.close()
    return pdf_bytes, scroll_height


def _html_to_pdf_bytes(html_text: str) -> bytes:
    pdf_bytes, _ = _html_to_pdf_bytes_and_height(html_text)
    return pdf_bytes


def render_single_page_resume_pdf(
    *,
    profile: MasterProfile,
    tailored: dict[str, Any],
    job: dict[str, Any],
    output_pdf_path: Path,
    contact: dict[str, str] | None = None,
    intern_availability: str = "",
) -> dict[str, Any]:
    """Render HTML resume to A4 PDF and enforce exact 1-page + unclipped + selectable Chinese text."""
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    working_tailored = {
        "summary": tailored.get("summary", ""),
        "selected": list(tailored.get("selected") or []),
    }

    page_count = 0
    text_len = 0
    compact_used = 0
    scroll_height = 0.0

    # Progressive compaction loop: level 0 -> 1 -> 2 -> trim tail bullets if >1 page
    for attempt in range(7):
        compact_level = min(attempt, 2)
        html_text = render_resume_html(
            profile=profile,
            tailored=working_tailored,
            job=job,
            contact=contact,
            compact_level=compact_level,
            intern_availability=intern_availability,
        )
        pdf_bytes, scroll_height = _html_to_pdf_bytes_and_height(html_text)
        output_pdf_path.write_bytes(pdf_bytes)

        reader = PdfReader(str(output_pdf_path))
        page_count = len(reader.pages)
        text_len = len((reader.pages[0].extract_text() or "").strip()) if page_count >= 1 else 0
        compact_used = attempt
        if page_count == 1 and scroll_height <= _A4_MAX_SCROLL_HEIGHT_PX:
            html_out = output_pdf_path.with_suffix(".html")
            html_out.write_text(html_text, encoding="utf-8")
            break
        if attempt >= 2 and len(working_tailored["selected"]) > 5:
            working_tailored["selected"].pop()

    return {
        "pdf_path": str(output_pdf_path),
        "page_count": page_count,
        "extracted_text_chars": text_len,
        "compact_attempts": compact_used,
        "scroll_height_px": round(scroll_height, 1),
        "selected_bullets_rendered": len(working_tailored["selected"]),
    }
