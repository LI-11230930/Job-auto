"""Scheme I (Starry Wisteria Plum x Frost White) Desktop Review Workbench UI HTML."""

from __future__ import annotations

REVIEW_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%232e1065'/%3E%3Ctext x='16' y='22' text-anchor='middle' font-size='18' font-family='sans-serif' font-weight='bold' fill='white'%3EJ%3C/text%3E%3C/svg%3E" />
<title>Job-auto · 智能求职助手 App</title>
<style>
  :root {
    --rail: #2e1065;
    --rail-deep: #1e0b47;
    --rail-hover: rgba(167, 139, 250, 0.20);
    --accent: #7c3aed;
    --accent-hover: #6d28d9;
    --accent-soft: #ede9fe;
    --accent-ink: #5b21b6;
    --bg: #f9f8fe;
    --card: #ffffff;
    --ink: #1e1b4b;
    --muted: #6b7280;
    --line: #e9d5ff;
    --line-soft: #f3e8ff;
    --good: #0f766e;
    --good-soft: #ecfdf5;
    --warn: #b45309;
    --warn-soft: #fffbeb;
    --bad: #b91c1c;
    --bad-soft: #fef2f2;
    --ease-press: cubic-bezier(0.2, 0.8, 0.2, 1);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: "Microsoft YaHei UI", "PingFang SC", system-ui, sans-serif;
    background: var(--bg);
    color: var(--ink);
    -webkit-font-smoothing: antialiased;
  }
  body.care-mode {
    font-size: 118%;
    --line: #a78bfa;
    --muted: #4b5563;
  }
  body.care-mode .btn, body.care-mode .track-btn, body.care-mode .chip { padding-top: 9px; padding-bottom: 9px; }

  .app-shell { display: grid; grid-template-columns: 72px 1fr; min-height: 100vh; }
  @media (max-width: 820px) { .app-shell { grid-template-columns: 1fr; } .slim-rail { flex-direction: row; padding: 8px 12px; overflow-x: auto; } }

  /* Left Arc-style Deep Plum Slim Rail */
  .slim-rail {
    background: linear-gradient(180deg, var(--rail) 0%, var(--rail-deep) 100%);
    color: #fff;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 14px 8px;
    gap: 10px;
    position: sticky;
    top: 0;
    height: 100vh;
    z-index: 30;
  }
  .rail-logo {
    width: 42px; height: 42px; border-radius: 13px;
    background: linear-gradient(135deg, #8b5cf6, #7c3aed);
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 20px; color: #fff;
    box-shadow: 0 8px 20px rgba(124, 58, 237, 0.42);
    margin-bottom: 6px; user-select: none;
  }
  .rail-btn {
    width: 56px; padding: 8px 4px; border: none; border-radius: 11px;
    background: transparent; color: #ddd6fe; cursor: pointer;
    display: flex; flex-direction: column; align-items: center; gap: 4px;
    font-size: 11px; font-weight: 600; text-decoration: none; position: relative;
    transition: transform 110ms var(--ease-press), background-color 140ms ease, color 140ms ease;
  }
  .rail-btn:hover { background: var(--rail-hover); color: #ffffff; }
  .rail-btn:active { transform: scale(0.95); }
  .rail-btn.active { background: var(--accent); color: #ffffff; box-shadow: 0 6px 16px rgba(124, 58, 237, 0.35); }
  .rail-ico { font-size: 16px; line-height: 1; }
  .rail-badge {
    position: absolute; top: 4px; right: 6px;
    background: #f43f5e; color: #fff; font-size: 10px; font-weight: 800;
    padding: 1px 5px; border-radius: 999px; display: none;
  }
  .rail-spacer { flex: 1; }

  /* Workspace Right Column */
  .workspace { display: flex; flex-direction: column; min-width: 0; }
  .topbar {
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--line);
    padding: 10px 20px;
    display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px;
    position: sticky; top: 0; z-index: 20;
  }
  .topbar-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .topbar-title h1 { margin: 0; font-size: 16.5px; font-weight: 800; color: var(--ink); }
  .privacy-tag {
    font-size: 11px; font-weight: 700; color: var(--accent-ink);
    background: var(--accent-soft); border: 1px solid var(--line);
    padding: 2px 9px; border-radius: 999px; cursor: pointer;
  }
  .summary-sub { font-size: 12px; color: var(--muted); margin-top: 2px; }
  .topbar-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; position: relative; }

  .capsule {
    display: none; align-items: center; gap: 7px;
    font-size: 12px; font-weight: 700; color: var(--accent-ink);
    background: var(--accent-soft); border: 1px solid #c4b5fd;
    padding: 5px 11px; border-radius: 999px;
  }
  .capsule.active { display: inline-flex; }
  .capsule-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); animation: pulse 1s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .35; } }

  .btn {
    border: 1px solid var(--line); background: #fff; color: var(--ink);
    padding: 7px 12px; border-radius: 9px; font-size: 12.5px; cursor: pointer; font-weight: 700;
    text-decoration: none; display: inline-flex; align-items: center; gap: 5px;
    transition: transform 110ms var(--ease-press), background-color 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
  }
  .btn:hover { background: var(--bg); border-color: #c4b5fd; }
  .btn:active { transform: scale(0.97); }
  .btn-primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .btn-primary:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
  .btn-soft { background: var(--accent-soft); border-color: #ddd6fe; color: var(--accent-ink); }
  .btn-warn { background: #d97706; border-color: #d97706; color: #fff; }
  .btn-danger { background: #dc2626; border-color: #dc2626; color: #fff; }
  .btn-outline { background: #fff; color: var(--ink); border: 1px solid var(--line); }

  /* Action Popover Menu (declutters top bar from 12 buttons down to 3 primary controls) */
  .more-menu-wrap { position: relative; }
  .more-popover {
    position: absolute; right: 0; top: calc(100% + 6px);
    width: 240px; background: #fff; border: 1.5px solid var(--line); border-radius: 12px;
    box-shadow: 0 18px 36px rgba(46, 16, 101, 0.14); padding: 8px; display: none; z-index: 40;
  }
  .more-popover.open { display: flex; flex-direction: column; gap: 4px; }
  .more-popover .btn { width: 100%; justify-content: flex-start; border-color: transparent; background: transparent; font-weight: 600; }
  .more-popover .btn:hover { background: var(--accent-soft); color: var(--accent-ink); }

  .layout { display: grid; grid-template-columns: 365px 1fr; flex: 1; min-height: 0; }
  @media (max-width: 1000px) { .layout { grid-template-columns: 1fr; } }

  /* Left Jobs Sidebar */
  .sidebar {
    background: var(--card); border-right: 1px solid var(--line);
    display: flex; flex-direction: column;
  }
  .track-bar { padding: 10px 12px 0; display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
  .track-btn {
    border: 1px solid var(--line); background: var(--bg); color: var(--ink);
    padding: 7px 6px; border-radius: 9px; font-size: 12px; font-weight: 700; cursor: pointer; text-align: center;
    transition: transform 110ms var(--ease-press), background-color 140ms;
  }
  .track-btn:active { transform: scale(0.97); }
  .track-btn.active { background: var(--rail); color: #fff; border-color: var(--rail); }
  .track-btn[data-type="实习"].active { background: var(--accent); border-color: var(--accent); }
  .filters { padding: 10px 12px; border-bottom: 1px solid var(--line); display: flex; gap: 6px; flex-wrap: wrap; }
  .chip {
    border: 1px solid var(--line); background: #fff; color: var(--muted);
    padding: 4px 10px; border-radius: 999px; font-size: 11.5px; cursor: pointer; font-weight: 600;
    transition: transform 110ms var(--ease-press), background-color 140ms;
  }
  .chip:active { transform: scale(0.96); }
  .chip.active { background: var(--accent); color: #fff; border-color: var(--accent); }
  .pkg-list { overflow-y: auto; flex: 1; padding: 10px; }

  .pkg-item {
    border: 1px solid var(--line); border-radius: 12px; padding: 11px 12px; margin-bottom: 8px;
    cursor: pointer; background: #fff;
    transition: transform 110ms var(--ease-press), border-color 150ms, box-shadow 150ms;
  }
  .pkg-item:hover { border-color: #a78bfa; box-shadow: 0 4px 12px rgba(124, 58, 237, 0.08); }
  .pkg-item:active { transform: scale(0.985); }
  .pkg-item.active { border-color: var(--accent); background: #faf7ff; box-shadow: inset 3.5px 0 0 var(--accent); }
  .pkg-top { display: flex; justify-content: space-between; gap: 8px; align-items: center; margin-bottom: 5px; }
  .score-badge { background: var(--rail); color: #fff; font-weight: 800; font-size: 11.5px; padding: 2px 8px; border-radius: 7px; }
  .type-badge { font-size: 11px; padding: 2px 7px; border-radius: 6px; font-weight: 700; }
  .type-campus { background: var(--accent-soft); color: var(--accent-ink); }
  .type-intern { background: #ccfbf1; color: #0f766e; }
  .pill { font-size: 11px; padding: 2px 8px; border-radius: 999px; font-weight: 700; background: #f3f4f6; color: #374151; }
  .pill-approve { background: var(--good-soft); color: var(--good); }
  .pill-later { background: var(--warn-soft); color: var(--warn); }
  .pill-reject { background: var(--bad-soft); color: var(--bad); }
  .pkg-title { font-size: 13.5px; font-weight: 700; color: var(--ink); margin-bottom: 3px; }
  .pkg-meta { font-size: 11.5px; color: var(--muted); }

  /* Optimistic shimmer skeleton */
  .skel-card { height: 76px; border-radius: 12px; border: 1px solid var(--line); margin-bottom: 8px; background: linear-gradient(90deg, #faf7ff 25%, #ede9fe 50%, #faf7ff 75%); background-size: 200% 100%; animation: shimmer 1.1s infinite; }
  @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

  /* Right Main Pane */
  .main { padding: 16px 20px; overflow-y: auto; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; margin-bottom: 14px; box-shadow: 0 2px 8px rgba(46, 16, 101, 0.03); }
  .privacy-banner {
    background: linear-gradient(135deg, #f5f3ff 0%, #ffffff 100%);
    border: 1.5px solid #c4b5fd; border-radius: 12px; padding: 12px 14px; margin-bottom: 14px;
    display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;
  }
  .detail-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-start; gap: 12px; }
  .detail-actions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 12px; }
  .note-input { padding: 7px 10px; border: 1px solid var(--line); border-radius: 8px; font-size: 13px; min-width: 210px; background: var(--bg); }
  .tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--line); margin-bottom: 12px; flex-wrap: wrap; }
  .tab-btn {
    border: none; background: transparent; padding: 8px 13px; font-size: 13px; font-weight: 700; color: var(--muted);
    cursor: pointer; border-bottom: 2.5px solid transparent;
    transition: color 140ms, border-color 140ms;
  }
  .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
  iframe.pdf-frame { width: 100%; height: 670px; border: 1px solid var(--line); border-radius: 10px; background: #fff; }
  pre.doc-box { white-space: pre-wrap; word-break: break-word; background: var(--bg); border: 1px solid var(--line); border-radius: 10px; padding: 12px; font-size: 12.5px; line-height: 1.55; margin: 0; font-family: inherit; }
  .qa-row { border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; margin-bottom: 8px; background: var(--bg); }
  .qa-q { font-weight: 700; font-size: 13px; margin-bottom: 4px; color: var(--rail); }
  .qa-a { font-size: 13px; color: var(--ink); line-height: 1.5; margin-bottom: 6px; }

  .queue-heading { font-size: 14px; font-weight: 700; color: var(--rail); margin: 12px 0 6px; padding-bottom: 4px; border-bottom: 1px solid var(--line); }
  .queue-toolbar { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; padding: 10px 12px; background: var(--bg); border: 1px solid var(--line); border-radius: 10px; margin-bottom: 12px; }
  .app-row { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; border-bottom: 0px solid var(--line-soft); padding: 10px 0; }
  .app-row:last-child { border-bottom: none; }
  .wf-badge { display: inline-block; font-size: 11px; padding: 2px 7px; border-radius: 6px; font-weight: 700; margin-left: 6px; }
  .wf-chat { background: #dcfce7; color: #166534; }
  .wf-portal { background: #fef3c7; color: #92400e; }
  .wf-email { background: #e0f2fe; color: #075985; }
  .wf-stale { background: var(--bad-soft); color: var(--bad); }

  /* Kanban Board (P7 View) */
  .kanban-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
  @media (max-width: 1100px) { .kanban-grid { grid-template-columns: repeat(2, 1fr); } }
  .kanban-col { background: var(--bg); border: 1px solid var(--line); border-radius: 11px; padding: 10px; min-height: 200px; }
  .kanban-hdr { font-size: 12.5px; font-weight: 800; color: var(--rail); margin-bottom: 8px; display: flex; justify-content: space-between; }
  .kanban-card { background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 8px 9px; margin-bottom: 7px; font-size: 12px; }

  .cfg-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; }
  .cfg-card { border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; background: var(--bg); }
  .cfg-card h3 { margin: 0 0 10px; font-size: 14.5px; color: var(--rail); }
  .cfg-field { margin-bottom: 10px; }
  .cfg-field label { display: block; font-size: 12px; font-weight: 700; color: #374151; margin-bottom: 4px; }
  .cfg-input, .cfg-select, .cfg-textarea { width: 100%; padding: 7px 10px; border: 1px solid #d8b4fe; border-radius: 8px; font-size: 13px; background: #fff; font-family: inherit; }
  .cfg-hint { font-size: 11.5px; color: var(--muted); margin-top: 4px; line-height: 1.45; }
  .cfg-row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

  /* Toast with Undo */
  .toast {
    position: fixed; right: 20px; bottom: 20px; background: var(--rail); color: #fff;
    padding: 10px 14px; border-radius: 11px; font-size: 13px; display: none; z-index: 60;
    box-shadow: 0 12px 28px rgba(46, 16, 101, 0.28); align-items: center; gap: 10px;
  }
  .toast-undo { background: #8b5cf6; color: #fff; border: none; border-radius: 6px; padding: 3px 9px; font-size: 12px; font-weight: 700; cursor: pointer; }

  /* Ctrl+K Command Palette */
  .cmd-backdrop {
    position: fixed; inset: 0; background: rgba(30, 11, 71, 0.45); backdrop-filter: blur(3px);
    display: none; align-items: flex-start; justify-content: center; padding-top: 10vh; z-index: 70;
  }
  .cmd-backdrop.open { display: flex; }
  .cmd-box {
    width: 100%; max-width: 560px; background: #fff; border: 1.5px solid #c4b5fd; border-radius: 14px;
    box-shadow: 0 24px 56px rgba(30, 11, 71, 0.28); overflow: hidden;
  }
  .cmd-input { width: 100%; border: none; border-bottom: 1px solid var(--line); padding: 14px 16px; font-size: 14.5px; outline: none; font-family: inherit; }
  .cmd-list { max-height: 320px; overflow-y: auto; padding: 6px; }
  .cmd-item { padding: 9px 12px; border-radius: 8px; cursor: pointer; display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; color: var(--ink); }
  .cmd-item:hover { background: var(--accent-soft); color: var(--accent-ink); }

  /* 5 Independent Top-Level Pages */
  .page-panel { display: none; padding: 14px 20px 28px; width: 100%; }
  .page-panel.active { display: block; }
  .page-header-bar {
    display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;
    background: var(--card); border: 1px solid var(--line); border-radius: 13px; padding: 12px 16px; margin-bottom: 14px;
  }
  .page-header-title { font-size: 15.5px; font-weight: 800; color: var(--rail); display: flex; align-items: center; gap: 8px; }
  .page-header-sub { font-size: 12px; color: var(--muted); margin-top: 2px; }

  /* Queue / Kanban Page: edge-to-edge list rows (no left/right gaps) + original Kanban 4 columns */
  #page-queue { padding: 0 0 24px; }
  #page-queue .page-header-bar {
    border-radius: 0; border-left: none; border-right: none; border-top: none;
    margin-bottom: 0; padding: 12px 16px;
  }
  #page-queue .queue-flat-card {
    background: var(--card); border: none; border-bottom: 1px solid var(--line);
    border-radius: 0; padding: 0; margin: 0; width: 100%; box-shadow: none;
  }
  #page-queue .queue-heading { margin: 0; padding: 8px 16px; background: #faf7ff; border-bottom: 1px solid var(--line); }
  #page-queue .app-row { padding: 10px 16px; margin: 0; width: 100%; }
  #page-queue .kanban-grid { padding: 12px; }
  .cal-wrap { padding: 12px 16px; }
  .cal-bar { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
  .cal-title { font-size: 14px; font-weight: 800; color: var(--rail); }
  .cal-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); border-top: 1px solid var(--line); border-left: 1px solid var(--line); border-radius: 8px; overflow: hidden; background: #fff; }
  .cal-dow { padding: 6px 8px; font-size: 11px; font-weight: 700; color: var(--muted); background: #faf7ff; border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); text-align: center; }
  .cal-cell { min-height: 86px; padding: 6px; border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); display: flex; flex-direction: column; gap: 3px; background: #fff; }
  .cal-cell.other { background: #fbfafe; color: #9ca3af; }
  .cal-cell.today { background: #f5f3ff; }
  .cal-day { font-size: 11px; font-weight: 700; color: var(--ink); display: flex; justify-content: space-between; }
  .cal-cell.other .cal-day { color: #9ca3af; }
  .cal-tag { font-size: 10.5px; line-height: 1.3; padding: 2px 5px; border-radius: 4px; background: #ede9fe; color: #4c1d95; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .cal-tag.dl { background: #fee2e2; color: #991b1b; }
  .cal-tag.sub { background: #dcfce7; color: #166534; }

  /* Full-Width Compact Message Strip (Inbox) */
  .msg-toolbar {
    display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap;
    background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 10px 14px; margin-bottom: 10px;
  }
  .msg-filters { display: inline-flex; gap: 6px; align-items: center; }
  .msg-list { display: flex; flex-direction: column; gap: 5px; width: 100%; }
  .msg-row {
    width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 12px;
    background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 6px 12px;
    transition: border-color 0.12s, background 0.12s;
  }
  .msg-row:hover { border-color: #c4b5fd; }
  .msg-row.unread { border-left: 3.5px solid var(--accent); background: #fdfcff; }
  .msg-row.read { opacity: 0.72; }
  .msg-main { flex: 1; min-width: 0; display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
  .msg-badge { font-size: 10.5px; font-weight: 800; padding: 1px 6px; border-radius: 5px; white-space: nowrap; }
  .msg-badge.new { background: var(--accent-soft); color: var(--accent-ink); }
  .msg-badge.old { background: #f3f4f6; color: #6b7280; }
  .msg-title { font-size: 12px; font-weight: 700; color: var(--ink); }
  .msg-body { font-size: 11px; color: #4b5563; line-height: 1.35; }
  .msg-time { font-size: 10.5px; color: var(--muted); white-space: nowrap; }
  .msg-actions { display: flex; gap: 6px; align-items: center; flex-shrink: 0; }
  .msg-btn {
    padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700;
    border: 1px solid #d8b4fe; background: #fff; color: var(--accent-ink); cursor: pointer; font-family: inherit;
  }
  .msg-btn:hover { background: var(--accent-soft); }

  /* Settings Page: Left Category Nav + White Minimalist Accordion Cards (Full Width, No Left/Right Margins) */
  #page-settings { padding: 0; }
  .cfg-shell { display: flex; gap: 0; align-items: stretch; width: 100%; max-width: none; margin: 0; min-height: calc(100vh - 64px); }
  @media (max-width: 860px) {
    .cfg-shell { flex-direction: column; min-height: auto; }
    .cfg-nav { width: 100% !important; position: static !important; flex-direction: row !important; flex-wrap: wrap; border-right: none !important; border-bottom: 1px solid var(--line); }
  }
  .cfg-nav { width: 210px; flex-shrink: 0; position: sticky; top: 64px; align-self: flex-start; min-height: calc(100vh - 64px); background: var(--card); border-right: 1px solid var(--line); padding: 14px 10px; display: flex; flex-direction: column; gap: 4px; }
  .cfg-nav-item {
    display: flex; align-items: center; gap: 10px; width: 100%; border: none; background: transparent;
    padding: 10px 12px; border-radius: 10px; font-size: 13.5px; font-weight: 700; color: #4b5563;
    cursor: pointer; text-align: left; font-family: inherit; transition: background 0.12s, color 0.12s;
  }
  .cfg-nav-item:hover { background: #f3f0ff; color: var(--accent-ink); }
  .cfg-nav-item.active { background: var(--accent-soft); color: var(--accent-ink); }
  .cfg-main { flex: 1; min-width: 0; max-width: none; padding: 16px 14px 28px; }
  .cfg-section { display: none; }
  .cfg-section.active { display: block; }
  .cfg-head { display: flex; align-items: center; gap: 14px; margin-bottom: 18px; }
  .cfg-head-ico {
    width: 46px; height: 46px; border-radius: 13px; background: var(--accent-soft); color: var(--accent-ink);
    display: flex; align-items: center; justify-content: center; font-size: 21px; flex-shrink: 0;
  }
  .cfg-head-title { font-size: 19px; font-weight: 800; color: var(--ink); margin: 0; }
  .cfg-head-sub { font-size: 12.5px; color: var(--muted); margin-top: 3px; }
  .acc-list { display: flex; flex-direction: column; gap: 11px; }
  .acc-card {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  .acc-card.open { border-color: #d8b4fe; box-shadow: 0 6px 20px rgba(124, 58, 237, 0.06); }
  .acc-hd {
    display: flex; align-items: flex-start; justify-content: space-between; gap: 16px;
    padding: 16px 20px; cursor: pointer; background: #ffffff; user-select: none;
  }
  .acc-hd:hover { background: #fcfbff; }
  .acc-title { font-size: 14.5px; font-weight: 800; color: #111827; margin-bottom: 4px; }
  .acc-desc { font-size: 12.5px; color: #6b7280; line-height: 1.5; }
  .acc-toggle {
    font-size: 18px; font-weight: 500; color: #6b7280; line-height: 1; padding-top: 2px;
    flex-shrink: 0; width: 20px; text-align: center;
  }
  .acc-body { display: none; padding: 14px 20px 18px; border-top: 1px solid #f3f4f6; background: #faf9fd; }
  .acc-card.open .acc-body { display: block; }

  /* Custom Global Filter Builder Chips (Single-Select & Multi-Select) */
  .cf-group { margin-bottom: 12px; padding: 10px 12px; background: #ffffff; border: 1px solid #ede9fe; border-radius: 10px; }
  .cf-label { display: flex; justify-content: space-between; align-items: center; font-size: 12.5px; font-weight: 800; color: var(--ink); margin-bottom: 7px; }
  .cf-mode-tag { font-size: 11px; font-weight: 700; padding: 1px 7px; border-radius: 999px; background: #f3f0ff; color: var(--accent-ink); }
  .cf-chip-row { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .cf-chip {
    border: 1px solid #ddd6fe; background: #ffffff; color: #4b5563;
    padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600;
    cursor: pointer; transition: all 120ms var(--ease-press); font-family: inherit;
  }
  .cf-chip:hover { border-color: var(--accent); color: var(--accent-ink); background: #faf7ff; }
  .cf-chip.active { background: var(--accent); color: #ffffff; border-color: var(--accent); }
  .cf-global-banner {
    display: none; padding: 7px 12px; background: #f5f3ff; border-bottom: 1px solid var(--line);
    font-size: 11.5px; color: var(--accent-ink); font-weight: 700; cursor: pointer;
    justify-content: space-between; align-items: center; gap: 6px;
  }
  .cf-global-banner.show { display: flex; }
  .cf-global-banner:hover { background: #ede9fe; }
  .cf-split { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(270px, 1fr); gap: 14px; align-items: start; }
  @media (max-width: 1080px) { .cf-split { grid-template-columns: 1fr; } }
  .cf-rule-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
  .cf-rule-card {
    background: #ffffff; border: 1px solid #ddd6fe; border-radius: 10px; padding: 10px;
    display: flex; flex-direction: column; gap: 7px;
  }
  .cf-rule-row1, .cf-rule-row2 { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
  .cf-inp-sm {
    border: 1px solid #d1d5db; border-radius: 7px; padding: 5px 8px; font-size: 12px;
    font-family: inherit; background: #fff; color: var(--ink);
  }
  .cf-inp-sm:focus { outline: none; border-color: var(--accent); }
  .cf-ref-box {
    background: #faf7ff; border: 1px dashed #c4b5fd; border-radius: 12px; padding: 12px;
  }
  .cf-ref-item {
    background: #ffffff; border: 1px solid #ede9fe; border-radius: 9px; padding: 8px 10px; margin-top: 8px;
  }
  .cf-ref-head { display: flex; justify-content: space-between; align-items: center; gap: 6px; margin-bottom: 3px; }
  .cf-ref-score { font-size: 11px; font-weight: 800; padding: 1px 7px; border-radius: 999px; background: #ede9fe; color: #5b21b6; }
  .cf-hits-line { margin-top: 4px; display: flex; gap: 4px; flex-wrap: wrap; }
  .cf-hit-tag { font-size: 10.5px; font-weight: 700; padding: 1px 6px; border-radius: 5px; background: #f3f0ff; color: #5b21b6; }

  /* Independent Page: Data Breakdown Kanban (数据板块) */
  .data-kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 12px; }
  .data-kpi-card {
    background: #ffffff; border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px;
    box-shadow: 0 2px 8px rgba(46, 16, 101, 0.03);
  }
  .data-kpi-label { font-size: 11.5px; color: var(--muted); font-weight: 700; margin-bottom: 4px; }
  .data-kpi-val { font-size: 22px; font-weight: 800; color: var(--rail); line-height: 1.2; }
  .data-kpi-sub { font-size: 11px; color: var(--accent-ink); margin-top: 3px; font-weight: 600; }
  .data-kanban-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 12px; }
  @media (max-width: 1180px) { .data-kanban-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  @media (max-width: 680px) { .data-kanban-grid { grid-template-columns: 1fr; } }
  .data-board-card { background: #ffffff; border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; }
  .data-board-title { font-size: 13px; font-weight: 800; color: var(--rail); margin-bottom: 9px; display: flex; justify-content: space-between; align-items: center; }
  .data-bar-row { display: flex; flex-direction: column; gap: 3px; margin-bottom: 7px; cursor: pointer; padding: 2px 4px; border-radius: 6px; }
  .data-bar-row:hover { background: #f5f3ff; }
  .data-bar-meta { display: flex; justify-content: space-between; font-size: 11.5px; font-weight: 700; color: var(--ink); }
  .data-bar-track { height: 6px; background: #f3f0ff; border-radius: 999px; overflow: hidden; }
  .data-bar-fill { height: 100%; background: linear-gradient(90deg, var(--rail), var(--accent)); border-radius: 999px; }
  .data-toolbar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 10px; }
  .data-job-row {
    display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;
    border-bottom: 1px solid var(--line); padding: 9px 4px;
  }
  .data-job-row:last-child { border-bottom: none; }
</style>
</head>
<body>
<div class="app-shell">
  <!-- Arc-Inspired Deep Plum Slim Rail -->
  <nav class="slim-rail" aria-label="主导航">
    <div class="rail-logo" title="Job-auto V1.5 (方案 I)">J</div>
    <button class="rail-btn active" data-rail="pdf" id="railPdf"><span class="rail-ico">📄</span><span>审阅</span></button>
    <button class="rail-btn" data-rail="inbox" id="btnTopMessages"><span class="rail-ico">🔔</span><span>消息</span><span class="rail-badge" id="railMsgBadge">0</span></button>
    <button class="rail-btn" data-rail="queue" id="btnTopQueue"><span class="rail-ico">📋</span><span>看板</span></button>
    <button class="rail-btn" data-rail="insights" id="btnTopInsights"><span class="rail-ico">📊</span><span>复盘</span></button>
    <button class="rail-btn" data-rail="data" id="btnTopData"><span class="rail-ico">🗂️</span><span>数据</span></button>
    <button class="rail-btn" data-rail="settings" id="btnTopSettings"><span class="rail-ico">⚙️</span><span>设置</span></button>
    <div class="rail-spacer"></div>
    <button class="rail-btn" id="btnCmdOpen" title="快捷键 Ctrl+K"><span class="rail-ico">⌘</span><span>命令</span></button>
    <button class="rail-btn" id="btnCareToggle" title="切换 120% 舒心大字模式"><span class="rail-ico">Aa</span><span>大字</span></button>
  </nav>

  <div class="workspace">
    <!-- Decluttered 3-Action Topbar -->
    <header class="topbar">
      <div>
        <div class="topbar-title">
          <h1>Job-auto · 智能求职助手 App</h1>
          <span class="privacy-tag" id="privacyBadge" title="点击查看隐私承诺说明">🔒 100% 本地 · 零第三方统计</span>
        </div>
        <div id="summaryLine" class="summary-sub">0.8s 缓存首屏加载中...</div>
      </div>

      <div class="topbar-actions">
        <div class="capsule" id="taskCapsule"><span class="capsule-dot"></span><span id="capsuleText">处理中...</span></div>
        <button class="btn btn-soft" id="btnOpenCmdTop">Ctrl+K 快捷命令</button>
        <button class="btn btn-primary" id="btnRunScreen">AI 智能匹配与定制</button>
        <div class="more-menu-wrap">
          <button class="btn btn-outline" id="btnMoreToggle">更多工具 ▾</button>
          <div class="more-popover" id="morePopover">
            <button class="btn" id="btnLaunchBrowser">启动插件抓岗浏览器 (9222)</button>
            <button class="btn" id="btnOneClickExpand">一键抓取新岗位 (公开源+Edge)</button>
            <button class="btn" id="btnSendEmail">发送今日提醒（App优先）</button>
            <button class="btn" id="btnExportQueue">导出待投递清单</button>
            <button class="btn" id="btnBuildDigest">生成今日简报</button>
            <button class="btn" id="btnSeedDemoTop">载入示例体验数据</button>
            <button class="btn" id="btnRefresh">刷新全盘数据</button>
          </div>
        </div>
      </div>
    </header>

    <div id="page-review" class="layout">
      <aside class="sidebar">
        <div class="track-bar" id="trackBar">
          <button class="track-btn active" data-type="all">全部批次</button>
          <button class="track-btn" data-type="校招">秋招 / 校招</button>
          <button class="track-btn" data-type="实习">实习</button>
        </div>
        <div class="filters" id="filterBar">
          <button class="chip active" data-filter="all">全部</button>
          <button class="chip" data-filter="pending">待审核</button>
          <button class="chip" data-filter="approve">已通过</button>
          <button class="chip" data-filter="later">暂缓</button>
          <button class="chip" data-filter="reject">已拒绝</button>
        </div>
        <div class="cf-global-banner" id="globalFilterBanner" title="点击前往「设置 -> 求职偏好与筛选」调整全局自定义口径">
          <span id="globalFilterBannerText">🎯 全局筛选生效中</span>
          <span style="text-decoration:underline;flex-shrink:0;">修改口径</span>
        </div>
        <div class="pkg-list" id="pkgList">
          <div class="skel-card"></div>
          <div class="skel-card"></div>
          <div class="skel-card"></div>
        </div>
      </aside>

      <main class="main">
        <!-- Privacy & Zero Telemetry Onboarding Trust Card -->
        <div class="privacy-banner" id="privacyBanner">
          <div style="font-size:12.5px;line-height:1.55;">
            <strong style="color:var(--rail);">透明隐私承诺（Local-First）：</strong>
            您的主简历、API Key 与全部岗位决策 100% 留在本机 SQLite；软件<b>严禁接入任何第三方统计埋点</b>；云端加密同步采用可插拔极简接口（未部署云端时自动回环演示 + 邮件兜底）。
          </div>
          <button class="btn btn-outline" id="btnDismissPrivacy" style="font-size:11.5px;padding:4px 10px;">知道了</button>
        </div>

        <div id="detailEmpty" class="card">
          <div style="font-size:16px;font-weight:800;color:var(--rail);margin-bottom:6px;">欢迎使用 Job-auto 独立桌面 App（方案 I · 星夜紫藤）</div>
          <div style="font-size:13px;color:var(--muted);margin-bottom:12px;line-height:1.6;">
            无需提前配好 Gemini Key 或服务器，你可以直接点击下方紫色按钮载入<b>内置 3 份脱敏示例岗位与单页定制简历 PDF</b> 立刻体验完整交互；也可以随时导入你自己的简历与任意大模型 Key。
          </div>
          <div id="systemStatusBox" style="background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:12px;font-size:12.5px;margin-bottom:12px;">应用自检中...</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <button class="btn btn-primary" id="btnSeedDemoHero">一键载入示例体验数据（免 Key 试用）</button>
            <button class="btn btn-soft" id="btnEmptySettings">打开偏好与模型设置</button>
            <button class="btn btn-outline" id="btnEmptyInbox">查看消息提醒中心</button>
            <button class="btn btn-outline" id="btnEmptyLaunchBrowser">启动插件抓岗浏览器 (9222)</button>
            <button class="btn btn-outline" id="btnEmptyExpand">一键抓取新岗位</button>
            <button class="btn btn-outline" id="btnEmptyBootstrap">初始化本地目录</button>
            <button class="btn btn-outline" id="btnEmptyQueue">查看投递看板</button>
          </div>
        </div>

        <div id="detailPane" style="display:none;">
          <div id="detailSummaryCard" class="card">
            <div class="detail-head">
              <div>
                <div id="dTitle" style="font-size:18.5px;font-weight:800;color:var(--ink);"></div>
                <div id="dMeta" style="font-size:12.5px;color:var(--muted);margin-top:4px;"></div>
              </div>
              <div style="display:flex;gap:8px;align-items:center;">
                <span id="dScore" class="score-badge"></span>
                <span id="dDecisionPill" class="pill"></span>
              </div>
            </div>
            <div id="dReasons" style="margin-top:10px;font-size:13px;line-height:1.55;"></div>
            <div id="dGaps" style="margin-top:6px;font-size:12.5px;color:var(--warn);"></div>
            <div id="dCompanyRow" style="margin-top:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px;">
              <span id="dCompanyBadge" class="pill">🏢 企业工商背调：暂未核查</span>
              <button type="button" class="btn btn-soft" id="btnVerifyCompanyNow" style="padding:4px 10px;font-size:12px;">🔍 查天眼查/企查查背调</button>
            </div>
            <div class="detail-actions">
              <input id="decisionNote" class="note-input" placeholder="可选：记录审核备注/投递要点..." />
              <a id="dPdfDownload" class="btn btn-outline">下载简历</a>
              <button class="btn btn-primary" data-act="approve">通过并加入投递队列</button>
              <button class="btn btn-warn" data-act="later">暂缓</button>
              <button class="btn btn-danger" data-act="reject">不考虑</button>
              <a id="dPortalLink" class="btn btn-outline" target="_blank" rel="noopener noreferrer">打开原岗位页面</a>
              <a id="dPdfLink" class="btn btn-outline" target="_blank" rel="noopener noreferrer">新窗口打开 PDF</a>
            </div>
          </div>

          <div id="tabsCard" class="card">
            <div class="tabs" id="tabBar">
              <button class="tab-btn active" data-tab="pdf">单页定制简历 PDF</button>
              <button class="tab-btn" data-tab="diff">事实核验对照与原 JD</button>
              <button class="tab-btn" data-tab="qa">打招呼话术与网申 QA</button>
            </div>

            <div id="tab-pdf"><iframe id="pdfFrame" class="pdf-frame" title="定制简历预览"></iframe></div>
            <div id="tab-diff" style="display:none;">
              <h3 style="margin:0 0 8px;font-size:14px;">定制微调对照（来源透明核验）</h3>
              <pre id="diffBox" class="doc-box"></pre>
              <h3 style="margin:14px 0 8px;font-size:14px;">原始岗位 JD</h3>
              <pre id="jdBox" class="doc-box"></pre>
            </div>
            <div id="tab-qa" style="display:none;">
              <div class="qa-row">
                <div class="qa-q">首句打招呼推荐话术</div>
                <div id="greetingText" class="qa-a"></div>
                <button class="btn btn-outline" id="btnCopyGreeting">复制打招呼话术</button>
              </div>
              <div id="qaList"></div>
            </div>
          </div>
        </div>
      </main>
    </div>

    <!-- Independent Page 2: Inbox (Full-Width Compact Strip Rows) -->
    <section id="page-inbox" class="page-panel" aria-label="消息通知中心">
      <div class="msg-toolbar">
        <div>
          <div class="page-header-title"><span>🔔 消息提醒中心</span></div>
          <div id="inboxSummary" class="page-header-sub">应用消息通知加载中...</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
          <div class="msg-filters" id="inboxFilterBar">
            <button class="chip active" data-inbox-filter="all">全部消息</button>
            <button class="chip" data-inbox-filter="unread">仅看未读</button>
          </div>
          <button class="btn btn-primary" id="btnTestAppNotify">发送测试桌面/手机提醒</button>
          <button class="btn btn-outline" id="btnMarkAllRead">全部标为已读</button>
        </div>
      </div>
      <div id="inboxList" class="msg-list"></div>
    </section>

    <!-- Independent Page 3: Queue & Kanban (Full-Width, Zero Horizontal Gap on List) -->
    <section id="page-queue" class="page-panel" aria-label="投递进度看板">
      <div class="page-header-bar">
        <div>
          <div class="page-header-title"><span>📋 投递进度看板</span></div>
          <div id="queueSummary" class="page-header-sub">投递方式统计加载中...</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <button class="btn btn-soft" id="btnToggleKanban">切换看板视图 (Kanban)</button>
          <button class="btn btn-soft" id="btnToggleCalendar">月度日历视图</button>
          <button class="btn btn-primary" id="btnPrepareDelivery">整理待投递包 &amp; 补全详情</button>
          <button class="btn btn-outline" id="btnExportAutofill">导出官网自动填写数据 (JSON)</button>
        </div>
      </div>
      <div class="queue-flat-card">
        <div id="appsList"></div>
      </div>
    </section>

    <!-- Independent Page 4: Insights -->
    <section id="page-insights" class="page-panel" aria-label="复盘与截止提醒">
      <div class="page-header-bar">
        <div>
          <div class="page-header-title"><span>📊 复盘与截止倒计时</span></div>
          <div id="insightsSummary" class="page-header-sub">复盘与提醒加载中...</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <button class="btn btn-primary" id="btnExportWeekly">导出每周复盘 (.md/.json)</button>
          <button class="btn btn-outline" id="btnRunRefreshCycle">一键刷新全链路产物</button>
        </div>
      </div>
      <div class="card">
        <div id="insightsBody"></div>
      </div>
    </section>

    <!-- Independent Page 5: Data (Captured Jobs Breakdown Kanban) -->
    <section id="page-data" class="page-panel" aria-label="岗位数据拆解看板">
      <div class="page-header-bar">
        <div>
          <div class="page-header-title"><span>🗂️ 岗位数据拆解看板</span></div>
          <div id="dataSummary" class="page-header-sub">正在汇总当前账号采集的全部本地岗位数据...</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <button class="btn btn-primary" id="btnDataExpand">一键抓取新岗位</button>
          <button class="btn btn-soft" id="btnDataJumpRules">调整自定义筛选规则</button>
          <button class="btn btn-outline" id="btnRefreshData">刷新数据看板</button>
        </div>
      </div>

      <div id="dataKpiGrid" class="data-kpi-grid"></div>
      <div id="dataKanbanGrid" class="data-kanban-grid"></div>

      <div class="card">
        <div class="data-toolbar">
          <input id="dataSearchInput" class="cf-inp-sm" style="flex:1;min-width:190px;" placeholder="搜索企业名称 / 职位 / 城市..." />
          <select id="dataSourceFilter" class="cf-inp-sm">
            <option value="all">全部来源</option>
            <option value="iguopin">国聘网</option>
            <option value="zhaopin">智联招聘</option>
            <option value="zhipin">Boss直聘</option>
            <option value="51job">前程无忧</option>
            <option value="ncss">国家24365</option>
            <option value="shixiseng">实习僧</option>
            <option value="campus_site">校招/手动</option>
            <option value="demo_sample">示例演示</option>
          </select>
          <select id="dataTypeFilter" class="cf-inp-sm">
            <option value="all">全部批次</option>
            <option value="校招">校招</option>
            <option value="实习">实习</option>
            <option value="未知">未标注</option>
          </select>
          <select id="dataStatusFilter" class="cf-inp-sm">
            <option value="active">仅活跃岗位</option>
            <option value="all">全部状态</option>
            <option value="filtered_out">已初筛过滤</option>
          </select>
          <label style="display:flex;align-items:center;gap:5px;font-size:12px;font-weight:700;cursor:pointer;">
            <input id="dataOnlyCustomMatched" type="checkbox" />
            <span>仅看自定义规则命中</span>
          </label>
          <button type="button" class="btn btn-soft" id="btnDataApplyFilter" style="padding:6px 12px;">查询</button>
          <button type="button" class="btn btn-outline" id="btnDataResetFilter" style="padding:6px 10px;">重置</button>
        </div>
        <div id="dataJobsMeta" style="font-size:12px;color:var(--muted);margin-bottom:8px;">加载明细中...</div>
        <div id="dataJobsRows"></div>
      </div>
    </section>

    <!-- Independent Page 6: Settings (Left Category Nav + Right Accordion Cards) -->
    <section id="page-settings" class="page-panel" aria-label="系统与偏好设置">
      <div class="cfg-shell">
        <aside class="cfg-nav" id="cfgNav" aria-label="设置分类">
          <button class="cfg-nav-item active" data-cfg-sec="models"><span>🤖</span><span>模型与云端中转</span></button>
          <button class="cfg-nav-item" data-cfg-sec="notify"><span>🔔</span><span>通知与备选邮箱</span></button>
          <button class="cfg-nav-item" data-cfg-sec="resume"><span>📄</span><span>个人主简历档案</span></button>
          <button class="cfg-nav-item" data-cfg-sec="prefs"><span>🎯</span><span>求职偏好与筛选</span></button>
          <button class="cfg-nav-item" data-cfg-sec="system"><span>🛠️</span><span>系统自检与目录</span></button>
        </aside>

        <div class="cfg-main">
          <!-- Category 1: AI & Cloud Relay -->
          <div class="cfg-section active" data-cfg-panel="models">
            <div class="cfg-head">
              <div class="cfg-head-ico">🤖</div>
              <div>
                <h2 class="cfg-head-title">模型与云端中转</h2>
                <div class="cfg-head-sub">自由切换 Gemini / DeepSeek / OpenAI 兼容 / Ollama，以及端到端加密云同步接口</div>
              </div>
            </div>
            <div class="acc-list">
              <div class="acc-card open">
                <div class="acc-hd">
                  <div>
                    <div class="acc-title">1. AI 大模型自由选择（支持任意 Key / 本地 Ollama）</div>
                    <div class="acc-desc">配置主力模型服务商、API Base URL、默认模型与本地 .env 密钥，支持一键连通性自检。</div>
                  </div>
                  <span class="acc-toggle">−</span>
                </div>
                <div class="acc-body">
                  <div class="cfg-field">
                    <label for="cfgLlmProvider">模型服务商</label>
                    <select id="cfgLlmProvider" class="cfg-select"></select>
                    <div id="cfgLlmHint" class="cfg-hint"></div>
                  </div>
                  <div class="cfg-field">
                    <label for="cfgLlmBaseUrl">API Base URL（OpenAI 兼容地址，Gemini 留空）</label>
                    <input id="cfgLlmBaseUrl" class="cfg-input" placeholder="例如 https://api.deepseek.com/v1" />
                  </div>
                  <div class="cfg-row2">
                    <div class="cfg-field">
                      <label for="cfgLlmModel">默认模型名称</label>
                      <input id="cfgLlmModel" class="cfg-input" placeholder="如 deepseek-chat / gemini-3.5-flash-lite" />
                    </div>
                    <div class="cfg-field">
                      <label for="cfgLlmKeyEnv">Key 变量名（写入本地 .env）</label>
                      <input id="cfgLlmKeyEnv" class="cfg-input" placeholder="如 DEEPSEEK_API_KEY" />
                    </div>
                  </div>
                  <div class="cfg-field">
                    <label for="cfgLlmApiKey">API Key（仅存本机 .env；留空保持不变）</label>
                    <input id="cfgLlmApiKey" type="password" class="cfg-input" placeholder="输入新的 API Key..." />
                    <div id="cfgLlmKeyState" class="cfg-hint"></div>
                  </div>
                  <div style="display:flex;gap:8px;flex-wrap:wrap;">
                    <button class="btn btn-primary" id="btnSaveLlmCfg">保存 AI 配置</button>
                    <button class="btn btn-outline" id="btnTestLlm">测试模型连通性</button>
                  </div>
                  <div id="cfgLlmTestResult" class="cfg-hint" style="margin-top:8px;"></div>
                </div>
              </div>

              <div class="acc-card" id="accRelayCard">
                <div class="acc-hd">
                  <div>
                    <div class="acc-title">2. 云端加密小中转接口（Cloudflare Workers / 自建 HTTPS）</div>
                    <div class="acc-desc">采用端到端 AES-256-GCM 密文中转；密钥仅存本地 .env，未连云端时可安全回环演示。</div>
                  </div>
                  <span class="acc-toggle">+</span>
                </div>
                <div class="acc-body">
                  <div class="cfg-row2">
                    <div class="cfg-field">
                      <label for="cfgRelayProvider">中转载体模式</label>
                      <select id="cfgRelayProvider" class="cfg-select">
                        <option value="none">暂未配置云服务器（本地回环演示）</option>
                        <option value="cloudflare_worker">Cloudflare Workers + KV/D1</option>
                        <option value="custom_http">自建轻服务器 HTTPS 接口</option>
                      </select>
                    </div>
                    <div class="cfg-field">
                      <label for="cfgRelayPairingId">设备配对 ID</label>
                      <input id="cfgRelayPairingId" class="cfg-input" placeholder="如 my-phone-01" />
                    </div>
                  </div>
                  <div class="cfg-field">
                    <label for="cfgRelayEndpoint">云端中转地址（留空自动回退本地安全存根）</label>
                    <input id="cfgRelayEndpoint" class="cfg-input" placeholder="https://relay.example.com（确认服务器后再填）" />
                  </div>
                  <div class="cfg-field">
                    <label for="cfgRelaySecret">端到端加密口令（写入本地 .env，绝不发给服务器）</label>
                    <input id="cfgRelaySecret" type="password" class="cfg-input" placeholder="输入配对加密口令..." />
                    <div id="cfgRelaySecretState" class="cfg-hint"></div>
                  </div>
                  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
                    <button class="btn btn-primary" id="btnSaveRelayCfg">保存中转接口配置</button>
                    <button class="btn btn-soft" id="btnRelayPush">立即加密推送到云端</button>
                    <button class="btn btn-soft" id="btnRelayPull">拉取手机端审批结果</button>
                    <button class="btn btn-soft" id="btnRelayPreview">生成密文试打包演示</button>
                    <a class="btn btn-soft" href="/relay-mobile" target="_blank" rel="noopener">打开手机端零知识审阅页</a>
                  </div>
                  <pre id="cfgRelayPreviewBox" class="doc-box" style="display:none;font-size:11.5px;"></pre>
                </div>
              </div>

              <div class="acc-card">
                <div class="acc-hd">
                  <div>
                    <div class="acc-title">3. 企业工商风控背调 MCP（天眼查 / 企查查 · 0 大模型 Token 消耗）</div>
                    <div class="acc-desc">AI 匹配与定制前直接通过 Streamable-HTTP MCP 核查高分候选企业工商存续与失信风险，本地缓存 30 天不重复扣额度。</div>
                  </div>
                  <span class="acc-toggle">+</span>
                </div>
                <div class="acc-body">
                  <div class="cfg-field">
                    <label style="display:flex;align-items:center;gap:8px;font-weight:800;cursor:pointer;">
                      <input type="checkbox" id="cfgCcEnabled" />
                      <span>在「AI 智能匹配与定制」前自动执行企业工商风控核查（不额外消耗 Gemini/LLM Token）</span>
                    </label>
                  </div>
                  <div class="cfg-row2">
                    <div class="cfg-field">
                      <label for="cfgCcProvider">背调 MCP 服务商</label>
                      <select id="cfgCcProvider" class="cfg-select"></select>
                      <div id="cfgCcHint" class="cfg-hint"></div>
                    </div>
                    <div class="cfg-field">
                      <label for="cfgCcUrl">Streamable-HTTP MCP 地址</label>
                      <input id="cfgCcUrl" class="cfg-input" placeholder="https://mcp.tianyancha.com/v1" />
                    </div>
                  </div>
                  <div class="cfg-row2">
                    <div class="cfg-field">
                      <label for="cfgCcKeyEnv">Key 环境变量名（写入本地 .env）</label>
                      <input id="cfgCcKeyEnv" class="cfg-input" placeholder="TYC_MCP_API_KEY" />
                    </div>
                    <div class="cfg-field">
                      <label for="cfgCcApiKey">API Key / Bearer Token（留空保持已保存的密钥）</label>
                      <input id="cfgCcApiKey" type="password" class="cfg-input" placeholder="输入天眼查或企查查 MCP Key..." />
                      <div id="cfgCcKeyState" class="cfg-hint"></div>
                    </div>
                  </div>
                  <div class="cfg-row3">
                    <div class="cfg-field">
                      <label for="cfgCcMinScore">最低触发分数线（仅查高分岗省额度）</label>
                      <input id="cfgCcMinScore" type="number" min="0" max="200" class="cfg-input" value="60" />
                    </div>
                    <div class="cfg-field">
                      <label for="cfgCcCacheDays">本地缓存天数（同公司不重查）</label>
                      <input id="cfgCcCacheDays" type="number" min="1" max="365" class="cfg-input" value="30" />
                    </div>
                    <div class="cfg-field" style="display:flex;align-items:flex-end;">
                      <label style="display:flex;align-items:center;gap:6px;font-size:12.5px;cursor:pointer;margin-bottom:8px;">
                        <input type="checkbox" id="cfgCcAutoReject" checked />
                        <span>注销/失信高危企业自动跳过定制</span>
                      </label>
                    </div>
                  </div>
                  <div style="display:flex;gap:8px;flex-wrap:wrap;">
                    <button class="btn btn-primary" id="btnSaveCompanyCheck">保存企业背调配置</button>
                    <button class="btn btn-soft" id="btnTestCompanyCheck">测试 MCP 连通与工具发现</button>
                  </div>
                  <div id="cfgCcTestResult" class="cfg-hint" style="margin-top:8px;"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Category 2: Notifications & Email -->
          <div class="cfg-section" data-cfg-panel="notify">
            <div class="cfg-head">
              <div class="cfg-head-ico">🔔</div>
              <div>
                <h2 class="cfg-head-title">通知与备选邮箱</h2>
                <div class="cfg-head-sub">App 消息中心与桌面弹窗优先；支持手机推送、备选邮箱 SMTP 兜底与每日定时简报</div>
              </div>
            </div>
            <div class="acc-list">
              <div class="acc-card open">
                <div class="acc-hd">
                  <div>
                    <div class="acc-title">1. 消息提醒策略与手机推送通道（App 优先 · 邮箱兜底）</div>
                    <div class="acc-desc">选择提醒优先级、桌面通知开关以及 Bark / ntfy 等手机端直达 Webhook。</div>
                  </div>
                  <span class="acc-toggle">−</span>
                </div>
                <div class="acc-body">
                  <div class="cfg-field">
                    <label for="cfgNotifyStrategy">提醒通道策略</label>
                    <select id="cfgNotifyStrategy" class="cfg-select">
                      <option value="app_first">优先 App 消息中心 + 桌面/手机推送，不可用时自动降级邮件（推荐）</option>
                      <option value="app_only">仅使用 App 消息中心与手机推送（完全不用邮箱）</option>
                      <option value="app_and_email">App 弹窗与邮箱通知同时发送</option>
                      <option value="email_only">仅使用邮箱 SMTP 发送</option>
                    </select>
                  </div>
                  <div class="cfg-field">
                    <label style="display:flex;align-items:center;gap:8px;">
                      <input type="checkbox" id="cfgDesktopNotify" checked /> 启用 App 内消息中心与桌面原生弹窗
                    </label>
                  </div>
                  <div class="cfg-field">
                    <label for="cfgPushPreset">手机端直达推送通道（Bark / ntfy 等）</label>
                    <select id="cfgPushPreset" class="cfg-select"></select>
                    <div id="cfgPushHint" class="cfg-hint"></div>
                  </div>
                  <div class="cfg-field">
                    <label for="cfgPushUrl">手机推送地址 / Key URL（写入本机 .env）</label>
                    <input id="cfgPushUrl" type="password" class="cfg-input" placeholder="例如 https://api.day.app/你的Key" />
                    <div id="cfgPushUrlState" class="cfg-hint"></div>
                  </div>
                  <div style="display:flex;gap:8px;flex-wrap:wrap;">
                    <button class="btn btn-primary" id="btnSaveEmailCfg">保存消息与邮箱设置</button>
                    <button class="btn btn-outline" id="btnTestAppNotifyCfg">测试 App / 手机弹窗</button>
                  </div>
                </div>
              </div>

              <div class="acc-card">
                <div class="acc-hd">
                  <div>
                    <div class="acc-title">2. 备选方案：邮箱 SMTP 设置</div>
                    <div class="acc-desc">推送通道不可达时自动通过 QQ / 163 / Gmail 或自定义 SMTP 发送简报邮件。</div>
                  </div>
                  <span class="acc-toggle">+</span>
                </div>
                <div class="acc-body">
                  <div class="cfg-field">
                    <label for="cfgEmailPreset">邮箱服务商（支持 QQ / 163 / Gmail / 自定义 SMTP）</label>
                    <select id="cfgEmailPreset" class="cfg-select"></select>
                    <div id="cfgEmailHint" class="cfg-hint"></div>
                  </div>
                  <div class="cfg-row2">
                    <div class="cfg-field">
                      <label for="cfgSmtpHost">SMTP 服务器</label>
                      <input id="cfgSmtpHost" class="cfg-input" placeholder="例如 smtp.163.com" />
                    </div>
                    <div class="cfg-field">
                      <label for="cfgSmtpPort">端口 &amp; 加密</label>
                      <div style="display:flex;gap:6px;">
                        <input id="cfgSmtpPort" class="cfg-input" style="width:76px;" placeholder="465" />
                        <select id="cfgSmtpSecurity" class="cfg-select">
                          <option value="auto">自动</option>
                          <option value="ssl">SSL</option>
                          <option value="starttls">STARTTLS</option>
                          <option value="none">无加密</option>
                        </select>
                      </div>
                    </div>
                  </div>
                  <div class="cfg-row2">
                    <div class="cfg-field">
                      <label for="cfgSmtpUser">发件邮箱</label>
                      <input id="cfgSmtpUser" class="cfg-input" placeholder="sender@example.com" />
                    </div>
                    <div class="cfg-field">
                      <label for="cfgEmailTo">接收简报邮箱</label>
                      <input id="cfgEmailTo" class="cfg-input" placeholder="默认同发件箱" />
                    </div>
                  </div>
                  <div class="cfg-field">
                    <label for="cfgSmtpPass">授权码（写入本地 .env；留空保持不变）</label>
                    <input id="cfgSmtpPass" type="password" class="cfg-input" placeholder="输入邮箱授权码..." />
                    <div id="cfgSmtpPassState" class="cfg-hint"></div>
                  </div>
                  <button class="btn btn-outline" id="btnTestEmail">发送备选测试邮件</button>
                </div>
              </div>

              <div class="acc-card">
                <div class="acc-hd">
                  <div>
                    <div class="acc-title">3. 每日定时推送与计划任务</div>
                    <div class="acc-desc">设定每天自动汇总新岗位与高分定制包并推送通知的时间。</div>
                  </div>
                  <span class="acc-toggle">+</span>
                </div>
                <div class="acc-body">
                  <label style="display:flex;align-items:center;gap:8px;font-size:12.5px;font-weight:700;margin-bottom:6px;flex-wrap:wrap;">
                    <input type="checkbox" id="cfgSchedEnabled" /> 开启每日定时推送
                    <input type="time" id="cfgSchedTime" value="16:00" style="padding:3px 6px;border:1px solid var(--line);border-radius:6px;" />
                    <button class="btn btn-outline" id="btnSaveSchedule" style="padding:4px 10px;">应用定时</button>
                  </label>
                  <div id="cfgSchedHint" class="cfg-hint"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Category 3: Master Resume -->
          <div class="cfg-section" data-cfg-panel="resume">
            <div class="cfg-head">
              <div class="cfg-head-ico">📄</div>
              <div>
                <h2 class="cfg-head-title">个人主简历档案</h2>
                <div class="cfg-head-sub">导入个人真实经历作为单页定制简历 PDF 与事实核验的唯一事实源（100% 留存本机）</div>
              </div>
            </div>
            <div class="acc-list">
              <div class="acc-card open">
                <div class="acc-hd">
                  <div>
                    <div class="acc-title">导入本地简历文件或粘贴正文（PDF / MD / TXT / JSON）</div>
                    <div class="acc-desc">系统将自动抽取项目与实习要点并生成本地 active master resume，严禁虚构任何经历。</div>
                  </div>
                  <span class="acc-toggle">−</span>
                </div>
                <div class="acc-body">
                  <div id="cfgMasterState" class="cfg-hint" style="margin-bottom:8px;font-weight:700;color:var(--ink);"></div>
                  <div class="cfg-field">
                    <label for="cfgResumeFile">选择本地简历文件</label>
                    <input id="cfgResumeFile" type="file" accept=".pdf,.txt,.md,.json" class="cfg-input" />
                  </div>
                  <div class="cfg-field">
                    <label for="cfgResumeText">或直接粘贴简历正文</label>
                    <textarea id="cfgResumeText" rows="5" class="cfg-textarea" placeholder="粘贴你的个人简历内容或经历摘要，点击下方即可生成本地主简历档案..."></textarea>
                  </div>
                  <button class="btn btn-primary" id="btnImportResume">一键导入简历并激活档案</button>
                </div>
              </div>
            </div>
          </div>

          <!-- Category 4: Preferences -->
          <div class="cfg-section" data-cfg-panel="prefs">
            <div class="cfg-head">
              <div class="cfg-head-ico">🎯</div>
              <div>
                <h2 class="cfg-head-title">求职偏好与筛选</h2>
                <div class="cfg-head-sub">设置届别、目标方向、首选城市、高分入包阈值及排除关键词</div>
              </div>
            </div>
            <div class="acc-list">
              <div class="acc-card open">
                <div class="acc-hd">
                  <div>
                    <div class="acc-title">基础求职画像与预筛阈值</div>
                    <div class="acc-desc">保存后即时生效；点击右侧按钮可立刻按最新偏好重跑 AI 智能匹配。</div>
                  </div>
                  <span class="acc-toggle">−</span>
                </div>
                <div class="acc-body">
                  <div class="cfg-row2">
                    <div class="cfg-field">
                      <label for="cfgProfYear">毕业届别</label>
                      <input id="cfgProfYear" class="cfg-input" type="number" placeholder="2027" />
                    </div>
                    <div class="cfg-field">
                      <label for="cfgProfMajor">专业 / 学历</label>
                      <input id="cfgProfMajor" class="cfg-input" placeholder="例如 会计学" />
                    </div>
                  </div>
                  <div class="cfg-field">
                    <label for="cfgTargetRoles">目标岗位方向（逗号分隔）</label>
                    <input id="cfgTargetRoles" class="cfg-input" placeholder="如 财务管培生, 审计助理, 数据分析" />
                  </div>
                  <div class="cfg-row2">
                    <div class="cfg-field">
                      <label for="cfgPrimaryCities">首选城市（逗号分隔）</label>
                      <input id="cfgPrimaryCities" class="cfg-input" placeholder="如 北京, 上海, 太原" />
                    </div>
                    <div class="cfg-field">
                      <label for="cfgMinScore">高分入包阈值（0-100）</label>
                      <input id="cfgMinScore" class="cfg-input" type="number" min="0" max="100" />
                    </div>
                  </div>
                  <div class="cfg-field">
                    <label for="cfgExcludedKw">排除关键词（逗号分隔）</label>
                    <input id="cfgExcludedKw" class="cfg-input" placeholder="如 销售, 电销, 催收, 兼职" />
                  </div>
                  <div style="display:flex;gap:8px;flex-wrap:wrap;">
                    <button class="btn btn-primary" id="btnSavePrefs">保存求职偏好</button>
                    <button class="btn btn-outline" id="btnSettingsRunScreen">运行 AI 智能匹配</button>
                  </div>
                </div>
              </div>

              <div class="acc-card open">
                <div class="acc-hd">
                  <div>
                    <div class="acc-title">2. 自定义筛选与评分规则（完全由您定义口径与分值 · 保存即全局生效）</div>
                    <div class="acc-desc">由使用者自由规定「哪个口径、单选或多选命中、加/减多少分、是否一票淘汰及总分合格线」；右侧提供参考口径与分值示例，可按需借鉴或一键套用后再改。</div>
                  </div>
                  <span class="acc-toggle">−</span>
                </div>
                <div class="acc-body">
                  <div class="cf-split">
                    <div>
                      <div class="cf-group">
                        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
                          <label style="display:flex;align-items:center;gap:7px;font-weight:800;font-size:13px;cursor:pointer;">
                            <input id="cfgCfEnabled" type="checkbox" />
                            <span>启用全局自定义规则（保存后对全 App 筛选/算分生效）</span>
                          </label>
                          <div class="cf-chip-row" id="cfModeGroup">
                            <button type="button" class="cf-chip active" data-cf-mode="override" title="仅按下方您自己的规则总分决定筛选与排序">接管评分与筛选</button>
                            <button type="button" class="cf-chip" data-cf-mode="blend" title="在 AI 原评分基础上叠加下方加减分规则">叠加 AI 评分微调</button>
                          </div>
                        </div>

                        <div class="cf-chip-row" id="cfScorePresets" style="gap:8px;">
                          <span style="font-size:12px;font-weight:700;color:var(--ink);">起始底分</span>
                          <input id="cfgCfBaseScore" class="cf-inp-sm" type="number" min="0" max="100" value="0" style="width:68px;" />
                          <span style="font-size:12px;font-weight:700;color:var(--ink);margin-left:6px;">入选最低总分线</span>
                          <input id="cfgCfMinScore" class="cf-inp-sm" type="number" min="0" max="200" value="60" style="width:74px;" />
                          <button type="button" class="cf-chip" data-cf-score="0">不限(0)</button>
                          <button type="button" class="cf-chip" data-cf-score="60">60分+</button>
                          <button type="button" class="cf-chip" data-cf-score="70">70分+</button>
                          <button type="button" class="cf-chip" data-cf-score="80">80分+</button>
                          <button type="button" class="cf-chip" data-cf-score="90">90分+</button>
                        </div>
                      </div>

                      <div class="cf-label" style="margin:6px 0;">
                        <span>我的筛选与算分口径（每条均可设单选/多选、加减分或一票排除）</span>
                        <button type="button" class="btn btn-soft" id="btnAddCfRule" style="padding:4px 10px;font-size:12px;">+ 新增一条规则</button>
                      </div>
                      <div id="cfRulesList" class="cf-rule-list"></div>

                      <details id="cfExtraDetails" style="margin:8px 0 12px;background:#fff;border:1px solid #ede9fe;border-radius:10px;padding:8px 12px;">
                        <summary id="cfExtraSummary" style="cursor:pointer;font-size:12px;font-weight:700;color:#4b5563;">附加快捷限定（可选：留空则完全交由上方规则决定）</summary>
                        <div style="margin-top:10px;">
                          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;">
                            <span style="font-size:11.5px;color:#6b7280;">注意：此处选中的项会作为“一票硬门槛”额外过滤所有岗位；若想完全按上方自定义规则打分排序，请保持全部未选。</span>
                            <button type="button" class="btn btn-outline" id="btnClearCfExtra" style="padding:3px 9px;font-size:11.5px;">清空全部附加快捷限定</button>
                          </div>
                          <div class="cf-group">
                            <div class="cf-label"><span>城市范围（单选）</span><span class="cf-mode-tag">单选 + 多选城市</span></div>
                            <div class="cf-chip-row" id="cfCityScopeGroup" style="margin-bottom:6px;">
                              <button type="button" class="cf-chip active" data-cf-city-scope="all">不限制</button>
                              <button type="button" class="cf-chip" data-cf-city-scope="primary_only">仅首选/指定</button>
                              <button type="button" class="cf-chip" data-cf-city-scope="primary_and_secondary">首选+备选</button>
                              <button type="button" class="cf-chip" data-cf-city-scope="allow_nationwide">含全国不限</button>
                            </div>
                            <div class="cf-chip-row" id="cfCityChips" style="margin-bottom:6px;">
                              <button type="button" class="cf-chip" data-cf-city="太原">太原</button>
                              <button type="button" class="cf-chip" data-cf-city="北京">北京</button>
                              <button type="button" class="cf-chip" data-cf-city="上海">上海</button>
                              <button type="button" class="cf-chip" data-cf-city="成都">成都</button>
                              <button type="button" class="cf-chip" data-cf-city="杭州">杭州</button>
                              <button type="button" class="cf-chip" data-cf-city="西安">西安</button>
                            </div>
                            <input id="cfgCfCities" class="cfg-input" placeholder="指定城市（逗号分隔，留空不限）" />
                          </div>
                          <div class="cfg-row2">
                            <div class="cf-group">
                              <div class="cf-label"><span>批次（可多选/单选）</span></div>
                              <div class="cf-chip-row" id="cfJobTypesGroup">
                                <button type="button" class="cf-chip" data-cf-jobtype="校招">秋招 / 校招</button>
                                <button type="button" class="cf-chip" data-cf-jobtype="实习">实习</button>
                              </div>
                            </div>
                            <div class="cf-group">
                              <div class="cf-label"><span>核验状态（可多选/单选）</span></div>
                              <div class="cf-chip-row" id="cfFactcheckGroup">
                                <button type="button" class="cf-chip" data-cf-fact="pass">通过 (pass)</button>
                                <button type="button" class="cf-chip" data-cf-fact="fallback_raw">自动回退</button>
                                <button type="button" class="cf-chip" data-cf-fact="warn">带告警</button>
                              </div>
                            </div>
                          </div>
                          <div class="cfg-row2">
                            <div class="cf-group">
                              <div class="cf-label"><span>投递渠道（可多选/单选）</span></div>
                              <div class="cf-chip-row" id="cfChannelsGroup">
                                <button type="button" class="cf-chip" data-cf-channel="company_portal">企业官网</button>
                                <button type="button" class="cf-chip" data-cf-channel="third_party">平台直聊</button>
                                <button type="button" class="cf-chip" data-cf-channel="email">邮箱直投</button>
                              </div>
                            </div>
                            <div class="cf-group">
                              <div class="cf-label"><span>来源站点（可多选/单选）</span></div>
                              <div class="cf-chip-row" id="cfSourcesGroup">
                                <button type="button" class="cf-chip" data-cf-source="iguopin">国聘网</button>
                                <button type="button" class="cf-chip" data-cf-source="zhaopin">智联</button>
                                <button type="button" class="cf-chip" data-cf-source="zhipin">Boss</button>
                                <button type="button" class="cf-chip" data-cf-source="51job">51job</button>
                                <button type="button" class="cf-chip" data-cf-source="ncss">24365</button>
                                <button type="button" class="cf-chip" data-cf-source="shixiseng">实习僧</button>
                                <button type="button" class="cf-chip" data-cf-source="campus_site">校招/手动</button>
                                <button type="button" class="cf-chip" data-cf-source="demo_sample">示例</button>
                              </div>
                            </div>
                          </div>
                          <input id="cfgCfIncludeKw" type="hidden" />
                          <input id="cfgCfExcludedKw" type="hidden" />
                        </div>
                      </details>

                      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
                        <button class="btn btn-primary" id="btnSaveCustomFilter">保存并全局启用规则</button>
                        <button class="btn btn-soft" id="btnSaveCustomFilterAndRun">保存并重跑 AI 匹配</button>
                        <button class="btn btn-outline" id="btnResetCustomFilter">恢复默认全放行</button>
                      </div>
                    </div>

                    <aside class="cf-ref-box" aria-label="参考口径与对应分数示例">
                      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:4px;">
                        <strong style="font-size:13px;color:var(--rail);">💡 参考口径与推荐分数示例</strong>
                        <button type="button" class="btn btn-outline" id="btnLoadRefTemplate" style="padding:3px 9px;font-size:11.5px;">一键导入参考模板</button>
                      </div>
                      <div style="font-size:11.5px;color:var(--muted);line-height:1.45;">
                        以下仅作为设定口径和分值的参考示范（按“满分100、入选线60~75分”思路设计）；点右侧「➕ 套用」可加入左侧列表自由改词、改分或设单/多选。
                      </div>
                      <div id="cfReferenceList"></div>
                    </aside>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Category 5: System Self-Check -->
          <div class="cfg-section" data-cfg-panel="system">
            <div class="cfg-head">
              <div class="cfg-head-ico">🛠️</div>
              <div>
                <h2 class="cfg-head-title">系统自检与目录</h2>
                <div class="cfg-head-sub">查看本机环境、抓岗浏览器 (CDP 9222) 与内置体验数据集，全部数据 100% 留存本机</div>
              </div>
            </div>
            <div class="acc-list">
              <div class="acc-card open">
                <div class="acc-hd">
                  <div>
                    <div class="acc-title">本机运行状态检查与常用操作</div>
                    <div class="acc-desc">快速初始化本地目录、启动带采集扩展的浏览器或载入 3 份脱敏示例岗位体验完整流程。</div>
                  </div>
                  <span class="acc-toggle">−</span>
                </div>
                <div class="acc-body">
                  <div id="systemStatusSettingsBox" style="background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px;font-size:12.5px;margin-bottom:12px;">应用自检中...</div>
                  <div style="display:flex;gap:8px;flex-wrap:wrap;">
                    <button class="btn btn-primary" id="btnSettingsSeedDemo">一键载入示例体验数据</button>
                    <button class="btn btn-outline" id="btnSettingsLaunchBrowser">启动抓岗浏览器 (9222)</button>
                    <button class="btn btn-outline" id="btnSettingsBootstrap">初始化本地目录与模板</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</div>

<!-- Toast with 3s Undo -->
<div id="toast" class="toast">
  <span id="toastText"></span>
  <button id="toastUndo" class="toast-undo" style="display:none;">撤销</button>
</div>

<!-- Ctrl+K Command Palette -->
<div class="cmd-backdrop" id="cmdBackdrop">
  <div class="cmd-box">
    <input class="cmd-input" id="cmdInput" placeholder="输入指令或搜索岗位关键词...（ESC 关闭）" />
    <div class="cmd-list" id="cmdList"></div>
  </div>
</div>

<script>
(() => {
  let currentFilter = 'all';
  let currentJobType = 'all';
  let currentTab = 'pdf';
  let packagesCache = [];
  let appsCache = [];
  let selectedPkgId = null;
  let kanbanMode = false;
  let calendarMode = false;
  const _calNow = new Date();
  let calendarYear = _calNow.getFullYear();
  let calendarMonth = _calNow.getMonth();
  let lastDecisionUndo = null;
  let toastTimer = null;

  const el = (id) => document.getElementById(id);
  const showToast = (msg, undoFn = null) => {
    const t = el('toast');
    const txt = el('toastText');
    const ubtn = el('toastUndo');
    txt.textContent = msg;
    if (typeof undoFn === 'function') {
      ubtn.style.display = 'inline-block';
      ubtn.onclick = async () => {
        ubtn.style.display = 'none';
        await undoFn();
      };
    } else {
      ubtn.style.display = 'none';
      ubtn.onclick = null;
    }
    t.style.display = 'flex';
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.style.display = 'none'; }, 3200);
  };

  const setCapsule = (active, text = '') => {
    const cap = el('taskCapsule');
    if (!cap) return;
    cap.classList.toggle('active', Boolean(active));
    if (text) el('capsuleText').textContent = text;
  };

  const decisionText = (d) => ({ pending: '待审核', approve: '已通过', later: '暂缓', reject: '已拒绝' }[d] || d);
  const trackText = (jt) => (jt === '实习' ? '实习' : '秋招/校招');

  // Restore local UI preferences (zero telemetry, localStorage only)
  try {
    if (localStorage.getItem('job_auto_care_mode') === '1') document.body.classList.add('care-mode');
    if (localStorage.getItem('job_auto_hide_privacy') === '1') {
      const pb = el('privacyBanner');
      if (pb) pb.style.display = 'none';
    }
    const cachedRaw = localStorage.getItem('job_auto_pkg_cache_v1');
    if (cachedRaw) {
      const parsed = JSON.parse(cachedRaw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        packagesCache = parsed;
        el('summaryLine').textContent = `已从 0.8s 本地缓存秒开 ${parsed.length} 份岗位（后台校对中...）`;
      }
    }
  } catch (_) {}

  el('btnCareToggle')?.addEventListener('click', () => {
    const on = document.body.classList.toggle('care-mode');
    try { localStorage.setItem('job_auto_care_mode', on ? '1' : '0'); } catch (_) {}
    showToast(on ? '已开启 120% 舒心大字与高对比模式' : '已切回标准精致字体尺寸');
  });

  el('btnDismissPrivacy')?.addEventListener('click', () => {
    const pb = el('privacyBanner');
    if (pb) pb.style.display = 'none';
    try { localStorage.setItem('job_auto_hide_privacy', '1'); } catch (_) {}
  });
  el('privacyBadge')?.addEventListener('click', () => {
    const pb = el('privacyBanner');
    if (pb) pb.style.display = 'flex';
  });

  const moreBtn = el('btnMoreToggle');
  const morePop = el('morePopover');
  moreBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    morePop.classList.toggle('open');
  });
  document.addEventListener('click', () => morePop?.classList.remove('open'));

  async function loadPackages() {
    const qs = new URLSearchParams({ decision: currentFilter, job_type: currentJobType });
    const res = await fetch('/api/packages?' + qs.toString());
    const data = await res.json();
    packagesCache = data.packages || [];
    try {
      localStorage.setItem('job_auto_pkg_cache_v1', JSON.stringify(packagesCache.slice(0, 30)));
    } catch (_) {}
    const cCnt = data.campus_count ?? 0;
    const iCnt = data.intern_count ?? 0;
    const allCnt = cCnt + iCnt;
    el('summaryLine').textContent = `当前列表 ${packagesCache.length} 份（秋招/校招 ${cCnt} · 实习 ${iCnt}） · 投递看板 ${data.applications_count || 0} 条`;
    const gfBanner = el('globalFilterBanner');
    if (gfBanner) {
      if (data.global_filter_active) {
        gfBanner.classList.add('show');
        el('globalFilterBannerText').textContent = `🎯 全局筛选：${data.global_filter_summary || '已启用'}`;
      } else {
        gfBanner.classList.remove('show');
      }
    }
    const tAll = document.querySelector('#trackBar [data-type="all"]');
    const tCam = document.querySelector('#trackBar [data-type="校招"]');
    const tInt = document.querySelector('#trackBar [data-type="实习"]');
    if (tAll) tAll.textContent = `全部 (${allCnt})`;
    if (tCam) tCam.textContent = `秋招/校招 (${cCnt})`;
    if (tInt) tInt.textContent = `实习 (${iCnt})`;
    renderPkgList();
    if (packagesCache.length > 0) {
      el('detailEmpty').style.display = 'none';
      el('detailSummaryCard').style.display = 'block';
      const exists = packagesCache.some(p => p.package_id === selectedPkgId);
      await selectPackage(exists ? selectedPkgId : packagesCache[0].package_id);
    } else {
      el('detailEmpty').style.display = 'block';
      el('detailPane').style.display = 'none';
    }
  }

  function renderPkgList() {
    const box = el('pkgList');
    box.replaceChildren();
    if (packagesCache.length === 0) {
      const empty = document.createElement('div');
      empty.style.padding = '20px 12px';
      empty.style.textAlign = 'center';
      empty.style.color = '#6b7280';
      empty.style.fontSize = '12.5px';
      empty.textContent = '暂无待审定制岗位，可点击右侧「一键载入示例体验数据」立刻试用。';
      box.appendChild(empty);
      return;
    }
    packagesCache.forEach((p) => {
      const card = document.createElement('div');
      card.className = 'pkg-item' + (p.package_id === selectedPkgId ? ' active' : '');
      card.onclick = () => selectPackage(p.package_id);

      const top = document.createElement('div');
      top.className = 'pkg-top';
      const leftBadges = document.createElement('div');
      leftBadges.style.display = 'flex';
      leftBadges.style.gap = '6px';
      leftBadges.style.alignItems = 'center';
      const sc = document.createElement('span');
      sc.className = 'score-badge';
      sc.textContent = `${p.score} 分`;
      const tb = document.createElement('span');
      tb.className = 'type-badge ' + (p.job_type === '实习' ? 'type-intern' : 'type-campus');
      tb.textContent = trackText(p.job_type);
      leftBadges.append(sc, tb);

      const pill = document.createElement('span');
      pill.className = 'pill ' + (p.decision !== 'pending' ? 'pill-' + p.decision : '');
      pill.textContent = decisionText(p.decision);
      top.append(leftBadges, pill);

      const title = document.createElement('div');
      title.className = 'pkg-title';
      title.textContent = `${p.company} · ${p.title}`;

      const meta = document.createElement('div');
      meta.className = 'pkg-meta';
      const cities = (p.cities || []).join('/') || '未知城市';
      meta.textContent = `${cities} · ${p.source} · 核验:${p.factcheck_status || 'pass'}`;

      card.append(top, title, meta);
      if (Array.isArray(p.custom_rule_hits) && p.custom_rule_hits.length > 0) {
        const hitsRow = document.createElement('div');
        hitsRow.className = 'cf-hits-line';
        p.custom_rule_hits.slice(0, 4).forEach((ht) => {
          const tag = document.createElement('span');
          tag.className = 'cf-hit-tag';
          tag.textContent = ht;
          hitsRow.appendChild(tag);
        });
        card.appendChild(hitsRow);
      }
      box.appendChild(card);
    });
  }

  async function selectPackage(pkgId) {
    selectedPkgId = pkgId;
    renderPkgList();
    const res = await fetch('/api/packages/' + encodeURIComponent(pkgId));
    const detail = await res.json();
    el('detailEmpty').style.display = 'none';
    el('detailPane').style.display = 'block';
    el('dTitle').textContent = `${detail.company} · ${detail.title}`;
    const cities = (detail.cities || []).join(' / ') || '未标注';
    el('dMeta').textContent = `岗位 #${detail.job_id} · ${detail.job_type} · ${cities} · 来源 ${detail.source} · 模型 ${detail.model}`;
    el('dScore').textContent = `${detail.score} 分`;
    const dp = el('dDecisionPill');
    dp.className = 'pill ' + (detail.decision !== 'pending' ? 'pill-' + detail.decision : '');
    dp.textContent = decisionText(detail.decision);

    const reasons = (detail.reasons || []).map(r => `[${r.dimension || '维度'} ${r.score || ''}] ${r.evidence || ''}`).join('；');
    el('dReasons').textContent = reasons ? '匹配依据：' + reasons : '';
    const gaps = (detail.gaps || []).join('；');
    el('dGaps').textContent = gaps ? '短板提示：' + gaps : '';
    el('decisionNote').value = detail.decision_reason || '';

    const pkgRow = packagesCache.find(p => p.package_id === pkgId);
    renderCompanyBadgeOnDetail(pkgRow?.company_check || detail.company_check || null, detail.company || '');

    const portalA = el('dPortalLink');
    if (detail.url) {
      portalA.href = detail.url;
      portalA.style.display = 'inline-flex';
    } else {
      portalA.style.display = 'none';
    }
    const pdfUrl = `/api/packages/${encodeURIComponent(pkgId)}/pdf`;
    el('dPdfDownload').href = `${pdfUrl}?download=1`;
    el('dPdfLink').href = pdfUrl;
    el('pdfFrame').src = `${pdfUrl}#view=FitH`;
    el('diffBox').textContent = detail.diff_md_text || '未找到 diff.md 文件';
    el('jdBox').textContent = detail.jd_text || '无正文';
    el('greetingText').textContent = detail.greeting || '';

    const qaList = el('qaList');
    qaList.replaceChildren();
    Object.entries(detail.qa || {}).forEach(([q, a]) => {
      const row = document.createElement('div');
      row.className = 'qa-row';
      const qDiv = document.createElement('div');
      qDiv.className = 'qa-q';
      qDiv.textContent = q;
      const aDiv = document.createElement('div');
      aDiv.className = 'qa-a';
      aDiv.textContent = String(a);
      const copyBtn = document.createElement('button');
      copyBtn.className = 'btn btn-outline';
      copyBtn.textContent = '复制回答';
      copyBtn.onclick = async () => {
        await navigator.clipboard.writeText(String(a));
        showToast('已复制：' + q);
      };
      row.append(qDiv, aDiv, copyBtn);
      qaList.appendChild(row);
    });
  }

  async function submitDecision(act, pkgOverride = null, skipUndo = false) {
    const targetId = pkgOverride || selectedPkgId;
    if (!targetId) return;
    const prevObj = packagesCache.find(p => p.package_id === targetId);
    const prevDec = prevObj?.decision || 'pending';
    const res = await fetch('/api/packages/' + encodeURIComponent(targetId) + '/decision', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision: act, reason: el('decisionNote').value || '' }),
    });
    if (!res.ok) {
      showToast('提交审核失败');
      return;
    }
    const undoFn = (!skipUndo && prevDec !== act && ['approve', 'later', 'reject'].includes(prevDec))
      ? () => submitDecision(prevDec, targetId, true)
      : null;
    showToast('已记录决定：' + decisionText(act), undoFn);
    await loadPackages();
    await loadApplications();
  }

  function normalizeCalendarDay(raw) {
    const m = String(raw || '').match(/(\\d{4})[-\\/](\\d{1,2})[-\\/](\\d{1,2})/);
    if (!m) return '';
    return m[1] + '-' + String(m[2]).padStart(2, '0') + '-' + String(m[3]).padStart(2, '0');
  }

  function renderCalendarMonthView(box) {
    const wrap = document.createElement('div');
    wrap.className = 'cal-wrap';

    const bar = document.createElement('div');
    bar.className = 'cal-bar';
    const title = document.createElement('div');
    title.className = 'cal-title';
    title.textContent = `${calendarYear} 年 ${calendarMonth + 1} 月 · 投递与截止日程月历`;
    const nav = document.createElement('div');
    nav.style.cssText = 'display:flex;gap:6px;align-items:center;';
    const mkBtn = (label, fn) => {
      const b = document.createElement('button');
      b.className = 'btn btn-soft';
      b.textContent = label;
      b.onclick = fn;
      return b;
    };
    nav.appendChild(mkBtn('‹ 上月', () => {
      calendarMonth -= 1;
      if (calendarMonth < 0) { calendarMonth = 11; calendarYear -= 1; }
      renderApplicationsView();
    }));
    nav.appendChild(mkBtn('本月', () => {
      const n = new Date();
      calendarYear = n.getFullYear();
      calendarMonth = n.getMonth();
      renderApplicationsView();
    }));
    nav.appendChild(mkBtn('下月 ›', () => {
      calendarMonth += 1;
      if (calendarMonth > 11) { calendarMonth = 0; calendarYear += 1; }
      renderApplicationsView();
    }));
    bar.appendChild(title);
    bar.appendChild(nav);
    wrap.appendChild(bar);

    const eventsByDay = new Map();
    const pushEvent = (dayKey, cls, text) => {
      if (!dayKey) return;
      if (!eventsByDay.has(dayKey)) eventsByDay.set(dayKey, []);
      eventsByDay.get(dayKey).push({ cls, text });
    };
    appsCache.forEach((a) => {
      const dlKey = normalizeCalendarDay(a.deadline);
      const subKey = normalizeCalendarDay(a.submitted_at);
      const crtKey = normalizeCalendarDay(a.created_at);
      if (dlKey) pushEvent(dlKey, 'dl', `⏰截止 ${a.company || ''}·${a.title || ''}`);
      if (subKey) pushEvent(subKey, 'sub', `📤已投 ${a.company || ''} (${a.status || ''})`);
      if (!dlKey && !subKey && crtKey) pushEvent(crtKey, '', `📌入列 ${a.company || ''}·${a.title || ''}`);
    });

    const grid = document.createElement('div');
    grid.className = 'cal-grid';
    ['周一', '周二', '周三', '周四', '周五', '周六', '周日'].forEach((d) => {
      const dow = document.createElement('div');
      dow.className = 'cal-dow';
      dow.textContent = d;
      grid.appendChild(dow);
    });

    const firstDay = new Date(calendarYear, calendarMonth, 1);
    const startOffset = (firstDay.getDay() + 6) % 7;
    const daysInMonth = new Date(calendarYear, calendarMonth + 1, 0).getDate();
    const totalCells = Math.ceil((startOffset + daysInMonth) / 7) * 7;
    const today = new Date();
    const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

    for (let idx = 0; idx < totalCells; idx += 1) {
      const cellDate = new Date(calendarYear, calendarMonth, idx - startOffset + 1);
      const y = cellDate.getFullYear();
      const m = cellDate.getMonth();
      const d = cellDate.getDate();
      const key = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

      const cell = document.createElement('div');
      cell.className = 'cal-cell' + (m !== calendarMonth ? ' other' : '') + (key === todayKey ? ' today' : '');
      const dayHdr = document.createElement('div');
      dayHdr.className = 'cal-day';
      dayHdr.innerHTML = `<span>${d}日</span>${key === todayKey ? '<span style="color:var(--accent);">今</span>' : ''}`;
      cell.appendChild(dayHdr);

      const evs = eventsByDay.get(key) || [];
      evs.slice(0, 3).forEach((ev) => {
        const tag = document.createElement('div');
        tag.className = 'cal-tag' + (ev.cls ? ' ' + ev.cls : '');
        tag.title = ev.text;
        tag.textContent = ev.text;
        cell.appendChild(tag);
      });
      if (evs.length > 3) {
        const more = document.createElement('div');
        more.style.cssText = 'font-size:10px;color:var(--muted);';
        more.textContent = `+ 还有 ${evs.length - 3} 项`;
        cell.appendChild(more);
      }
      grid.appendChild(cell);
    }

    wrap.appendChild(grid);
    box.appendChild(wrap);
  }

  function renderApplicationsView() {
    const box = el('appsList');
    box.replaceChildren();
    if (calendarMode) {
      renderCalendarMonthView(box);
      return;
    }
    if (kanbanMode) {
      const cols = [
        { key: '待提交', title: '待提交', filter: (a) => a.status === '待提交' },
        { key: '已投递', title: '已投递 / 跟进中', filter: (a) => a.status === '已投递' },
        { key: '笔面试', title: '笔试 / 面试', filter: (a) => a.status === '笔试' || a.status === '面试' },
        { key: '归档', title: 'Offer / 暂缓 / 拒绝', filter: (a) => ['Offer', '暂缓', '已拒绝'].includes(a.status) },
      ];
      const grid = document.createElement('div');
      grid.className = 'kanban-grid';
      cols.forEach((col) => {
        const colRows = appsCache.filter(col.filter);
        const cEl = document.createElement('div');
        cEl.className = 'kanban-col';
        const hdr = document.createElement('div');
        hdr.className = 'kanban-hdr';
        hdr.innerHTML = `<span>${col.title}</span><span>${colRows.length}</span>`;
        cEl.appendChild(hdr);
        if (colRows.length === 0) {
          const emp = document.createElement('div');
          emp.style.fontSize = '11.5px';
          emp.style.color = '#9ca3af';
          emp.textContent = '空';
          cEl.appendChild(emp);
        }
        colRows.forEach((a) => {
          const kc = document.createElement('div');
          kc.className = 'kanban-card';
          kc.innerHTML = `<div style="font-weight:700;color:var(--ink);">${a.company}</div><div style="color:var(--muted);margin:2px 0;">${a.title}</div><div style="color:var(--accent-ink);font-weight:700;">${a.status} · ${a.score || '--'}分</div>`;
          cEl.appendChild(kc);
        });
        grid.appendChild(cEl);
      });
      box.appendChild(grid);
      return;
    }

    const campusRows = appsCache.filter((a) => (a.job_type || '校招') !== '实习');
    const internRows = appsCache.filter((a) => a.job_type === '实习');
    appendQueueSection(box, '秋招 / 校招投递队列', campusRows);
    appendQueueSection(box, '实习投递队列', internRows);
  }

  function appendQueueSection(box, headingText, rows) {
    const h = document.createElement('div');
    h.className = 'queue-heading';
    h.textContent = `${headingText}（${rows.length} 条）`;
    box.appendChild(h);
    if (rows.length === 0) {
      const emp = document.createElement('div');
      emp.style.color = '#6b7280';
      emp.style.fontSize = '12.5px';
      emp.textContent = '暂无已确认记录';
      box.appendChild(emp);
      return;
    }
    rows.forEach((a) => {
      const row = document.createElement('div');
      row.className = 'app-row';
      const info = document.createElement('div');
      const strong = document.createElement('strong');
      strong.textContent = `${a.company} · ${a.title}`;
      const wfBadge = document.createElement('span');
      const wf = a.workflow_mode || (a.apply_channel === 'email' ? 'email_send' : (a.apply_channel === 'third_party' ? 'chat_direct' : 'portal_autofill'));
      if (wf === 'chat_direct') {
        wfBadge.className = 'wf-badge wf-chat';
        wfBadge.textContent = '直聊话术投递';
      } else if (wf === 'email_send') {
        wfBadge.className = 'wf-badge wf-email';
        wfBadge.textContent = '邮件附件投递';
      } else {
        wfBadge.className = 'wf-badge wf-portal';
        wfBadge.textContent = '官网网申自动填写';
      }
      info.append(strong, wfBadge);
      if (a.is_stale_pending) {
        const sb = document.createElement('span');
        sb.className = 'wf-badge wf-stale';
        sb.textContent = '待投递超期>7天';
        info.appendChild(sb);
      }
      const sub = document.createElement('div');
      sub.style.fontSize = '12px';
      sub.style.color = '#6b7280';
      sub.style.marginTop = '3px';
      const targetText = a.apply_target ? ` · 投递目标：${a.apply_target}` : '';
      sub.textContent = `状态：${a.status} · 匹配 ${a.score} 分 · ${a.applied_at || '待确认提交时间'}${targetText}`;
      info.appendChild(sub);

      const ctrl = document.createElement('div');
      ctrl.style.display = 'flex';
      ctrl.style.gap = '6px';
      ctrl.style.flexWrap = 'wrap';
      if (wf === 'portal_autofill') {
        const openBtn = document.createElement('button');
        openBtn.className = 'btn btn-outline';
        openBtn.textContent = '在 Edge 打开网申';
        openBtn.onclick = async () => {
          const r = await fetch(`/api/applications/${a.id}/open-edge`, { method: 'POST' });
          const d = await r.json();
          showToast(d.ok ? '已唤起浏览器定位到网申页面' : (d.error || '打开失败'));
        };
        ctrl.appendChild(openBtn);
      }
      if (a.package_id) {
        const pdfLink = document.createElement('a');
        pdfLink.className = 'btn btn-outline';
        pdfLink.href = `/api/packages/${a.package_id}/pdf?download=1`;
        pdfLink.textContent = '下载定制简历';
        ctrl.appendChild(pdfLink);
      }
      const sel = document.createElement('select');
      sel.className = 'note-input';
      sel.style.minWidth = '110px';
      ['待提交', '已投递', '笔试', '面试', 'Offer', '已拒绝', '暂缓'].forEach(st => {
        const opt = document.createElement('option');
        opt.value = st;
        opt.textContent = st;
        if (st === a.status) opt.selected = true;
        sel.appendChild(opt);
      });
      const saveBtn = document.createElement('button');
      saveBtn.className = 'btn btn-primary';
      saveBtn.textContent = '更新状态';
      saveBtn.onclick = async () => {
        await fetch(`/api/applications/${a.id}/status`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: sel.value }),
        });
        showToast('投递状态已更新：' + sel.value);
        await loadApplications();
      };
      ctrl.append(sel, saveBtn);
      row.append(info, ctrl);
      box.appendChild(row);
    });
  }

  async function loadApplications() {
    const [res, sumRes] = await Promise.all([
      fetch('/api/applications'),
      fetch('/api/applications/summary'),
    ]);
    const data = await res.json();
    const sum = await sumRes.json();
    const sumEl = el('queueSummary');
    if (sumEl) {
      const bc = sum.by_channel || {};
      const stale = sum.stale_pending_count || 0;
      sumEl.textContent = `总队列 ${sum.total || 0} 条 · 官网网申 ${bc.portal_autofill || 0} · 直聊话术 ${bc.chat_direct || 0} · 邮件投递 ${bc.email_send || 0}` + (stale ? ` · 超期未投 ${stale} 条` : '');
    }
    appsCache = data.applications || [];
    renderApplicationsView();
  }

  function syncQueueViewButtons() {
    if (el('btnToggleKanban')) {
      el('btnToggleKanban').textContent = kanbanMode ? '切换列表视图' : '切换看板视图 (Kanban)';
    }
    if (el('btnToggleCalendar')) {
      el('btnToggleCalendar').textContent = calendarMode ? '返回列表视图' : '月度日历视图';
    }
  }

  el('btnToggleKanban')?.addEventListener('click', () => {
    kanbanMode = !kanbanMode;
    if (kanbanMode) calendarMode = false;
    syncQueueViewButtons();
    renderApplicationsView();
  });

  el('btnToggleCalendar')?.addEventListener('click', () => {
    calendarMode = !calendarMode;
    if (calendarMode) kanbanMode = false;
    syncQueueViewButtons();
    renderApplicationsView();
  });

  function appendInsightCard(parent, title, lines) {
    const card = document.createElement('div');
    card.className = 'qa-row';
    const h = document.createElement('div');
    h.className = 'qa-q';
    h.textContent = title;
    card.appendChild(h);
    if (!lines || lines.length === 0) {
      const p = document.createElement('div');
      p.className = 'qa-a';
      p.style.color = '#6b7280';
      p.textContent = '暂无需要关注的记录';
      card.appendChild(p);
    } else {
      lines.forEach((ln) => {
        const p = document.createElement('div');
        p.className = 'qa-a';
        p.textContent = '• ' + ln;
        card.appendChild(p);
      });
    }
    parent.appendChild(card);
  }

  async function loadStage5Overview() {
    const res = await fetch('/api/stage5/overview');
    const data = await res.json();
    const rem = data.reminders || {};
    const rep = data.weekly_report || {};
    const insEl = el('insightsSummary');
    if (insEl) {
      insEl.textContent = `今日提醒 ${rem.total_alerts || 0} 项（7日截止 ${(rem.deadline_soon || []).length} · 已投未回 ${(rem.followup_due || []).length} · 笔面试 ${(rem.interview_upcoming || []).length}）`;
    }
    const body = el('insightsBody');
    if (!body) return;
    body.replaceChildren();
    const alertLines = [];
    (rem.deadline_soon || []).slice(0, 5).forEach((x) => {
      alertLines.push(`[即将截止 剩${x.days_left}天] ${x.company} · ${x.title}（${x.deadline}）`);
    });
    (rem.followup_due || []).slice(0, 5).forEach((x) => {
      alertLines.push(`[已投${x.days_since}天未推进] ${x.company} · ${x.title}`);
    });
    (rem.interview_upcoming || []).slice(0, 5).forEach((x) => {
      alertLines.push(`[${x.status}备战] ${x.company} · ${x.title}`);
    });
    appendInsightCard(body, '一、今日重点提醒与跟进', alertLines);
    const tracks = rep.tracks || {};
    const funnelLines = Object.entries(tracks).map(([name, m]) => (
      `${name}：推荐 ${m.total_packages} → 通过 ${m.approved_packages} (${m.approve_rate}%) → 已投 ${m.submitted_applications} → 笔面试 ${m.interview_or_offer}`
    ));
    appendInsightCard(body, '二、近 7 天双赛道转化漏斗', funnelLines);
    appendInsightCard(body, '三、参数调优与复盘建议', rep.suggestions || []);
    const runLines = (rep.recent_runs || []).slice(0, 6).map(
      (r) => `#${r.id} [${r.run_type}] ${r.status} · ${r.started_at || ''}`
    );
    appendInsightCard(body, '四、最近本地运行记录', runLines);
  }

  function switchMainTab(tabName) {
    currentTab = tabName;
    const isReview = ['pdf', 'diff', 'qa', 'review'].includes(tabName);
    const activeSubTab = isReview ? (tabName === 'review' ? 'pdf' : tabName) : 'pdf';
    document.querySelectorAll('.slim-rail .rail-btn[data-rail]').forEach(r => {
      const target = r.dataset.rail;
      const isMatch = target === tabName || (target === 'pdf' && isReview);
      r.classList.toggle('active', isMatch);
    });
    const revEl = el('page-review');
    if (revEl) revEl.style.display = isReview ? 'grid' : 'none';
    ['inbox', 'queue', 'insights', 'data', 'settings'].forEach(p => {
      const panel = el('page-' + p);
      if (panel) panel.classList.toggle('active', p === tabName);
    });
    if (isReview) {
      document.querySelectorAll('#tabBar .tab-btn').forEach(c => c.classList.toggle('active', c.dataset.tab === activeSubTab));
      ['pdf', 'diff', 'qa'].forEach(k => {
        const sub = el('tab-' + k);
        if (sub) sub.style.display = k === activeSubTab ? 'block' : 'none';
      });
      if (packagesCache.length === 0) {
        el('detailEmpty').style.display = 'block';
        el('detailPane').style.display = 'none';
      } else {
        el('detailEmpty').style.display = 'none';
        el('detailPane').style.display = 'block';
        el('detailSummaryCard').style.display = 'block';
      }
    } else if (tabName === 'inbox') {
      loadNotifications();
    } else if (tabName === 'queue') {
      loadApplications();
    } else if (tabName === 'insights') {
      loadStage5Overview();
    } else if (tabName === 'data') {
      loadDataDashboard();
    } else if (tabName === 'settings') {
      loadSettingsPanel();
      loadSystemStatus();
    }
  }

  el('railPdf')?.addEventListener('click', () => switchMainTab('pdf'));
  el('tabBar').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-tab]');
    if (!btn) return;
    switchMainTab(btn.dataset.tab);
  });

  el('trackBar').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-type]');
    if (!btn) return;
    currentJobType = btn.dataset.type;
    document.querySelectorAll('#trackBar .track-btn').forEach(b => b.classList.toggle('active', b.dataset.type === currentJobType));
    loadPackages();
  });

  el('filterBar').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-filter]');
    if (!btn) return;
    currentFilter = btn.dataset.filter;
    document.querySelectorAll('#filterBar .chip').forEach(c => c.classList.toggle('active', c.dataset.filter === currentFilter));
    loadPackages();
  });

  el('btnTopQueue').addEventListener('click', () => switchMainTab('queue'));
  el('btnTopInsights').addEventListener('click', () => switchMainTab('insights'));
  el('btnTopData')?.addEventListener('click', () => switchMainTab('data'));
  el('btnTopMessages')?.addEventListener('click', () => switchMainTab('inbox'));
  el('btnEmptyInbox')?.addEventListener('click', () => switchMainTab('inbox'));
  el('btnEmptyQueue')?.addEventListener('click', () => switchMainTab('queue'));
  el('btnTopSettings')?.addEventListener('click', () => switchMainTab('settings'));
  el('btnEmptySettings')?.addEventListener('click', () => switchMainTab('settings'));

  document.querySelectorAll('[data-act]').forEach(btn => {
    btn.addEventListener('click', () => submitDecision(btn.dataset.act));
  });

  el('btnCopyGreeting').addEventListener('click', async () => {
    await navigator.clipboard.writeText(el('greetingText').textContent || '');
    showToast('已复制打招呼话术');
  });

  el('btnExportQueue').addEventListener('click', async () => {
    const res = await fetch('/api/export-queue', { method: 'POST' });
    const d = await res.json();
    showToast(`已导出 ${d.count} 条待投递清单到 output/digest/`);
  });

  el('btnBuildDigest').addEventListener('click', async () => {
    const res = await fetch('/api/digest', { method: 'POST' });
    const d = await res.json();
    showToast(`简报已生成（含 ${d.packages_count} 份投递包）`);
  });

  el('btnExportAutofill').addEventListener('click', async () => {
    const res = await fetch('/api/export-autofill', { method: 'POST' });
    const d = await res.json();
    showToast(`已导出到 local/autofill_extension_backup.json（含 ${d.profiles_exported} 套档案）`);
  });

  el('btnPrepareDelivery').addEventListener('click', async () => {
    setCapsule(true, '整理投递包中...');
    const res = await fetch('/api/prepare-delivery', { method: 'POST' });
    const d = await res.json();
    setCapsule(false);
    showToast(`已整理 ${d.prepared_count} 个待投递包（补全详情 ${d.enriched_count} 项）`);
    await loadApplications();
  });

  el('btnExportWeekly').addEventListener('click', async () => {
    const res = await fetch('/api/stage5/weekly-report', { method: 'POST' });
    const d = await res.json();
    showToast(`周报已导出：${d.report_md_path || 'output/reports/'}`);
    await loadStage5Overview();
  });

  el('btnRunRefreshCycle').addEventListener('click', async () => {
    setCapsule(true, '全链路刷新中...');
    const res = await fetch('/api/stage5/refresh-cycle', { method: 'POST' });
    const d = await res.json();
    setCapsule(false);
    showToast(`全链路产物已刷新（run #${d.run_id}）`);
    await loadPackages();
    await loadApplications();
    await loadStage5Overview();
  });

  async function triggerSeedDemo() {
    setCapsule(true, '正在载入示例岗位与单页 PDF...');
    const res = await fetch('/api/system/seed-demo', { method: 'POST' });
    const d = await res.json();
    setCapsule(false);
    showToast(d.message || '示例体验数据已就绪');
    await loadPackages();
    await loadNotifications();
    await loadSystemStatus();
  }
  el('btnSeedDemoHero')?.addEventListener('click', triggerSeedDemo);
  el('btnSeedDemoTop')?.addEventListener('click', triggerSeedDemo);

  async function loadSystemStatus() {
    try {
      const res = await fetch('/api/system/status');
      const s = await res.json();
      const dot = (ok, label) => `<span class="pill ${ok ? 'pill-approve' : 'pill-later'}" style="margin-right:6px;">${ok ? 'OK' : '待配置'} · ${label}</span>`;
      const html =
        `<div style="margin-bottom:8px;">` +
        dot(s.env_exists, '.env') +
        dot(s.user_config_exists, '偏好文件') +
        dot(s.master_loaded, '主简历档案') +
        dot(s.gemini_key_set, 'AI 模型 Key') +
        dot(s.smtp_ready, '备选邮箱') +
        dot(s.edge_cdp_active, '抓岗浏览器 9222') +
        `</div>` +
        `<div style="color:#4b5563;">本地岗位库 <strong>${s.total_jobs}</strong> 条（活跃 ${s.active_jobs}） · 内置采集扩展 ${(s.extensions || []).length} 个 · 浏览器：${s.browser_found ? '已定位' : '待检测'}</div>`;
      if (el('systemStatusBox')) el('systemStatusBox').innerHTML = html;
      if (el('systemStatusSettingsBox')) el('systemStatusSettingsBox').innerHTML = html;
    } catch (_) {}
  }

  let inboxFilter = 'all';
  el('inboxFilterBar')?.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-inbox-filter]');
    if (!btn) return;
    inboxFilter = btn.dataset.inboxFilter || 'all';
    document.querySelectorAll('#inboxFilterBar .chip').forEach(c => c.classList.toggle('active', c.dataset.inboxFilter === inboxFilter));
    loadNotifications();
  });

  async function loadNotifications() {
    try {
      const res = await fetch('/api/notifications?limit=40');
      const d = await res.json();
      const unread = Number(d.unread_count || 0);
      const badge = el('railMsgBadge');
      if (badge) {
        badge.textContent = String(unread);
        badge.style.display = unread > 0 ? 'inline-block' : 'none';
      }
      const allItems = d.items || [];
      const items = inboxFilter === 'unread' ? allItems.filter(n => !n.is_read) : allItems;
      const sumEl = el('inboxSummary');
      if (sumEl) sumEl.textContent = `未读提醒 ${unread} 条 · 共保存 ${allItems.length} 条本地应用消息`;
      const listEl = el('inboxList');
      if (!listEl) return;
      listEl.replaceChildren();
      if (items.length === 0) {
        const emp = document.createElement('div');
        emp.className = 'card';
        emp.style.color = '#6b7280';
        emp.style.fontSize = '12px';
        emp.textContent = inboxFilter === 'unread'
          ? '暂无未读提醒。点击「全部消息」可查看历史记录。'
          : '暂无提醒消息。点击「发送测试桌面/手机提醒」或载入示例数据即可查看效果。';
        listEl.appendChild(emp);
        return;
      }
      items.forEach((n) => {
        const row = document.createElement('div');
        row.className = 'msg-row ' + (n.is_read ? 'read' : 'unread');

        const main = document.createElement('div');
        main.className = 'msg-main';
        const b = document.createElement('span');
        b.className = 'msg-badge ' + (n.is_read ? 'old' : 'new');
        b.textContent = n.is_read ? '已读' : '新提醒';
        const title = document.createElement('span');
        title.className = 'msg-title';
        title.textContent = n.title || '';
        const body = document.createElement('span');
        body.className = 'msg-body';
        body.textContent = n.body || '';
        main.append(b, title, body);

        const act = document.createElement('div');
        act.className = 'msg-actions';
        const tm = document.createElement('span');
        tm.className = 'msg-time';
        tm.textContent = n.created_at || '';
        act.appendChild(tm);
        if (!n.is_read) {
          const markBtn = document.createElement('button');
          markBtn.className = 'msg-btn';
          markBtn.textContent = '标为已读';
          markBtn.onclick = async () => {
            await fetch('/api/notifications/read', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ ids: [n.id] }),
            });
            await loadNotifications();
          };
          act.appendChild(markBtn);
        }
        row.append(main, act);
        listEl.appendChild(row);
      });
    } catch (_) {}
  }

  let llmPresetsCache = [];
  let emailPresetsCache = [];
  let pushPresetsCache = [];

  let ccPresetsCache = [];
  let currentDetailCompany = '';

  function renderCompanyBadgeOnDetail(cc, companyName) {
    currentDetailCompany = companyName || '';
    const badge = el('dCompanyBadge');
    if (!badge) return;
    if (!cc || !cc.risk_level || cc.risk_level === 'unknown') {
      badge.className = 'pill';
      badge.textContent = cc?.risk_summary ? `🏢 ${cc.risk_summary}` : '🏢 企业工商背调：暂未核查（点右侧按钮即时查询）';
      return;
    }
    const cls = cc.risk_level === 'severe' ? 'pill-reject' : (cc.risk_level === 'warning' ? 'pill-later' : 'pill-approve');
    const icon = cc.risk_level === 'severe' ? '🚨 高危避坑' : (cc.risk_level === 'warning' ? '⚠️ 需留意' : '🛡️ 工商存续正常');
    badge.className = 'pill ' + cls;
    badge.textContent = `${icon} · ${cc.risk_summary || cc.reg_status || ''}`;
  }

  function applyCompanyCheckPresetFields(presetId) {
    const p = ccPresetsCache.find(item => item.id === presetId);
    if (!p) return;
    if (el('cfgCcHint')) el('cfgCcHint').textContent = p.hint || '';
    if (el('cfgCcUrl') && presetId !== 'custom_mcp') el('cfgCcUrl').value = p.mcp_url || '';
    if (el('cfgCcKeyEnv') && p.default_key_env) el('cfgCcKeyEnv').value = p.default_key_env;
  }

  function applyLlmPresetFields(presetId) {
    const p = llmPresetsCache.find(item => item.id === presetId);
    if (!p) return;
    el('cfgLlmHint').textContent = p.hint || '';
    if (p.base_url !== undefined) el('cfgLlmBaseUrl').value = p.base_url || '';
    if (p.default_model) el('cfgLlmModel').value = p.default_model;
    if (p.api_key_env) el('cfgLlmKeyEnv').value = p.api_key_env;
  }

  function applyEmailPresetFields(presetId) {
    const p = emailPresetsCache.find(item => item.id === presetId);
    if (!p) return;
    el('cfgEmailHint').textContent = p.hint || '';
    if (p.host !== undefined && presetId !== 'custom') el('cfgSmtpHost').value = p.host;
    if (p.port) el('cfgSmtpPort').value = String(p.port);
    if (p.security) el('cfgSmtpSecurity').value = p.security;
  }

  async function loadSettingsPanel() {
    try {
      const res = await fetch('/api/system/settings');
      const d = await res.json();
      llmPresetsCache = d.llm_presets || [];
      emailPresetsCache = d.email_presets || [];
      pushPresetsCache = d.push_presets || [];

      const llmSel = el('cfgLlmProvider');
      llmSel.replaceChildren();
      llmPresetsCache.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.label;
        llmSel.appendChild(opt);
      });
      llmSel.value = d.llm?.primary_provider || 'gemini_interactions';
      const curLlm = llmPresetsCache.find(x => x.id === llmSel.value);
      el('cfgLlmHint').textContent = curLlm?.hint || '';
      el('cfgLlmBaseUrl').value = d.llm?.base_url || '';
      el('cfgLlmModel').value = d.llm?.default_model || '';
      el('cfgLlmKeyEnv').value = d.llm?.api_key_env || '';
      el('cfgLlmKeyState').textContent = d.llm?.api_key_set ? `已配置密钥：${d.llm.api_key_masked}` : '当前未配置该服务商 Key（示例模式可免 Key 体验）';

      const mailSel = el('cfgEmailPreset');
      mailSel.replaceChildren();
      emailPresetsCache.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.label;
        mailSel.appendChild(opt);
      });
      el('cfgNotifyStrategy').value = d.notifications?.strategy || 'app_first';
      el('cfgDesktopNotify').checked = d.notifications?.desktop_notify_enabled !== false;

      const pushSel = el('cfgPushPreset');
      if (pushSel) {
        pushSel.replaceChildren();
        pushPresetsCache.forEach(p => {
          const opt = document.createElement('option');
          opt.value = p.id;
          opt.textContent = p.label;
          pushSel.appendChild(opt);
        });
        pushSel.value = d.notifications?.push_preset || 'none';
        const curPush = pushPresetsCache.find(x => x.id === pushSel.value);
        el('cfgPushHint').textContent = curPush?.hint || '';
        el('cfgPushUrl').placeholder = curPush?.placeholder || 'https://...';
        el('cfgPushUrlState').textContent = d.notifications?.push_webhook_set
          ? `已保存手机推送地址：${d.notifications.push_webhook_masked}`
          : '未配置手机推送地址（如仅使用电脑桌面弹窗可留空）';
      }

      mailSel.value = d.notifications?.email_preset || 'qq';
      const curMail = emailPresetsCache.find(x => x.id === mailSel.value);
      el('cfgEmailHint').textContent = curMail?.hint || '';
      el('cfgSmtpHost').value = d.notifications?.smtp_host || '';
      el('cfgSmtpPort').value = String(d.notifications?.smtp_port || 465);
      el('cfgSmtpSecurity').value = d.notifications?.smtp_security || 'auto';
      el('cfgSmtpUser').value = d.notifications?.smtp_user || '';
      el('cfgEmailTo').value = d.notifications?.email_to || '';
      el('cfgSmtpPassState').textContent = d.notifications?.smtp_pass_set ? `已配置授权码：${d.notifications.smtp_pass_masked}` : '未设置授权码';

      const sch = d.schedule || {};
      el('cfgSchedEnabled').checked = Boolean(sch.enabled);
      el('cfgSchedTime').value = sch.send_time || '16:00';
      el('cfgSchedHint').textContent = sch.supported
        ? `当前状态：${sch.enabled ? '已开启 (' + sch.send_time + ' ' + (sch.timezone || '') + ')' : '未启用'}`
        : (sch.note || '当前系统请配合 crontab 使用');

      const m = d.master || {};
      el('cfgMasterState').textContent = m.loaded
        ? `当前主简历档案：${m.version_tag}（要点 ${m.bullets} 条）`
        : '尚未导入个人简历档案：可上传文件或直接点击页面上方的「一键载入示例」。';

      el('cfgProfYear').value = String(d.profile?.graduation_year || 2027);
      el('cfgProfMajor').value = d.profile?.major || '';
      el('cfgTargetRoles').value = (d.profile?.target_roles || []).join(', ');
      el('cfgPrimaryCities').value = (d.preferences?.primary_cities || []).join(', ');
      el('cfgMinScore').value = String(d.scoring?.min_score_for_package ?? 80);
      el('cfgExcludedKw').value = (d.preferences?.excluded_keywords || []).join(', ');

      const cf = d.preferences?.custom_filter || {};
      refTemplatesCache = d.filter_reference_templates || [];
      if (el('cfgCfEnabled')) {
        el('cfgCfEnabled').checked = Boolean(cf.enabled);
        const cfMode = cf.mode || 'override';
        document.querySelectorAll('#cfModeGroup .cf-chip').forEach((b) => {
          b.classList.toggle('active', b.dataset.cfMode === cfMode);
        });
        if (el('cfgCfBaseScore')) el('cfgCfBaseScore').value = String(cf.base_score ?? 0);
        const cfScore = Number(cf.min_display_score ?? 60);
        el('cfgCfMinScore').value = String(cfScore);
        document.querySelectorAll('#cfScorePresets .cf-chip').forEach((b) => {
          b.classList.toggle('active', Number(b.dataset.cfScore) === cfScore);
        });
        customRulesState = Array.isArray(cf.rules)
          ? cf.rules.map((r, i) => ({
              id: r.id || `rule_${i + 1}`,
              name: r.name || '',
              enabled: r.enabled !== false,
              field: r.field || 'any_text',
              match_mode: r.match_mode || 'multi_any',
              values: Array.isArray(r.values) ? [...r.values] : [],
              action: r.action || 'add',
              score: Number(r.score ?? 20),
            }))
          : [];
        if (typeof renderCustomRules === 'function') renderCustomRules();
        if (typeof renderFilterReferences === 'function') renderFilterReferences();

        const cScope = cf.city_scope || 'all';
        document.querySelectorAll('#cfCityScopeGroup .cf-chip').forEach((b) => {
          b.classList.toggle('active', b.dataset.cfCityScope === cScope);
        });
        const setMulti = (sel, attr, vals) => {
          const picked = new Set((vals || []).map((x) => String(x)));
          document.querySelectorAll(sel).forEach((b) => {
            b.classList.toggle('active', picked.has(String(b.dataset[attr] || '')));
          });
        };
        const cfCities = cf.custom_cities || [];
        el('cfgCfCities').value = cfCities.join(', ');
        setMulti('#cfCityChips .cf-chip', 'cfCity', cfCities);
        setMulti('#cfJobTypesGroup .cf-chip', 'cfJobtype', cf.job_types);
        setMulti('#cfFactcheckGroup .cf-chip', 'cfFact', cf.factcheck_statuses);
        setMulti('#cfChannelsGroup .cf-chip', 'cfChannel', cf.apply_channels);
        setMulti('#cfSourcesGroup .cf-chip', 'cfSource', cf.sources);
        if (el('cfgCfIncludeKw')) el('cfgCfIncludeKw').value = (cf.include_keywords || []).join(', ');
        if (el('cfgCfExcludedKw')) el('cfgCfExcludedKw').value = (cf.excluded_keywords || []).join(', ');
      }

      const cr = d.cloud_relay || {};
      if (el('cfgRelayProvider')) {
        el('cfgRelayProvider').value = cr.provider || 'none';
        el('cfgRelayPairingId').value = cr.pairing_id || 'demo-pair-local';
        el('cfgRelayEndpoint').value = cr.endpoint_url || '';
        el('cfgRelaySecretState').textContent = cr.relay_secret_set
          ? `已配置端到端配对口令：${cr.relay_secret_masked}`
          : '未设置口令（演示时自动生成本机临时密钥，不会上传云端）';
      }

      ccPresetsCache = d.company_check_presets || [];
      const cc = d.company_check || {};
      const ccSel = el('cfgCcProvider');
      if (ccSel) {
        ccSel.replaceChildren();
        ccPresetsCache.forEach((p) => {
          const opt = document.createElement('option');
          opt.value = p.id;
          opt.textContent = p.label;
          ccSel.appendChild(opt);
        });
        ccSel.value = cc.provider || 'tianyancha_mcp';
        const curCc = ccPresetsCache.find(x => x.id === ccSel.value);
        if (el('cfgCcHint')) el('cfgCcHint').textContent = curCc?.hint || '';
        if (el('cfgCcEnabled')) el('cfgCcEnabled').checked = Boolean(cc.enabled);
        if (el('cfgCcUrl')) el('cfgCcUrl').value = cc.mcp_url || '';
        if (el('cfgCcKeyEnv')) el('cfgCcKeyEnv').value = cc.api_key_env || 'TYC_MCP_API_KEY';
        if (el('cfgCcMinScore')) el('cfgCcMinScore').value = String(cc.min_score_to_check ?? 60);
        if (el('cfgCcCacheDays')) el('cfgCcCacheDays').value = String(cc.cache_days ?? 30);
        if (el('cfgCcAutoReject')) el('cfgCcAutoReject').checked = cc.auto_reject_severe_risk !== false;
        if (el('cfgCcKeyState')) {
          el('cfgCcKeyState').textContent = cc.api_key_set
            ? `已保存背调密钥：${cc.api_key_masked}`
            : '尚未填入 API Key / Token（天眼查可前往 https://ai.tianyancha.com 免费申请）';
        }
      }
    } catch (_) {}
  }

  el('cfgLlmProvider')?.addEventListener('change', (e) => applyLlmPresetFields(e.target.value));
  el('cfgEmailPreset')?.addEventListener('change', (e) => applyEmailPresetFields(e.target.value));
  el('cfgPushPreset')?.addEventListener('change', (e) => {
    const p = pushPresetsCache.find(item => item.id === e.target.value);
    if (!p) return;
    el('cfgPushHint').textContent = p.hint || '';
    if (p.placeholder) el('cfgPushUrl').placeholder = p.placeholder;
  });

  el('btnSaveLlmCfg')?.addEventListener('click', async () => {
    const payload = {
      llm: {
        primary_provider: el('cfgLlmProvider').value,
        base_url: el('cfgLlmBaseUrl').value.trim(),
        default_model: el('cfgLlmModel').value.trim(),
        api_key_env: el('cfgLlmKeyEnv').value.trim(),
        api_key: el('cfgLlmApiKey').value.trim(),
      },
    };
    const res = await fetch('/api/system/settings', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    const d = await res.json();
    el('cfgLlmApiKey').value = '';
    showToast(res.ok ? `已保存 AI 模型配置（${d.primary_provider}）` : (d.detail || '保存失败'));
    await loadSettingsPanel();
    await loadSystemStatus();
  });

  el('btnTestLlm')?.addEventListener('click', async () => {
    el('cfgLlmTestResult').textContent = '正在测试模型连通性...';
    const res = await fetch('/api/system/test-llm', { method: 'POST' });
    const d = await res.json();
    el('cfgLlmTestResult').textContent = d.ok ? `连通成功 [${d.provider} / ${d.model}]` : `连通失败：${d.error || '未知错误'}`;
    showToast(d.ok ? '模型连通测试通过' : '模型连通测试失败');
  });

  el('cfgCcProvider')?.addEventListener('change', (e) => applyCompanyCheckPresetFields(e.target.value));

  el('btnSaveCompanyCheck')?.addEventListener('click', async () => {
    const prov = el('cfgCcProvider')?.value || 'tianyancha_mcp';
    const enabled = Boolean(el('cfgCcEnabled')?.checked) && prov !== 'none';
    const payload = {
      company_check: {
        enabled,
        provider: prov,
        mcp_url: el('cfgCcUrl')?.value.trim() || '',
        api_key_env: el('cfgCcKeyEnv')?.value.trim() || 'TYC_MCP_API_KEY',
        api_key: el('cfgCcApiKey')?.value.trim() || '',
        min_score_to_check: Number(el('cfgCcMinScore')?.value || 60),
        cache_days: Number(el('cfgCcCacheDays')?.value || 30),
        auto_reject_severe_risk: Boolean(el('cfgCcAutoReject')?.checked),
      },
    };
    const res = await fetch('/api/system/settings', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    const d = await res.json();
    if (el('cfgCcApiKey')) el('cfgCcApiKey').value = '';
    showToast(res.ok ? '已保存企业工商风控背调设置' : (d.detail || '保存失败'));
    await loadSettingsPanel();
  });

  el('btnTestCompanyCheck')?.addEventListener('click', async () => {
    if (el('cfgCcTestResult')) el('cfgCcTestResult').textContent = '正在连接 MCP 网关并拉取 tools/list...';
    const res = await fetch('/api/system/test-company-check', { method: 'POST' });
    const d = await res.json();
    if (el('cfgCcTestResult')) {
      el('cfgCcTestResult').textContent = d.status === 'ok'
        ? `✅ ${d.message}（工具示例：${(d.sample_tools || []).slice(0, 5).join(', ')}）`
        : `⚠️ ${d.error || d.message || '连接未就绪'}`;
    }
    showToast(d.status === 'ok' ? '企业背调 MCP 连通成功' : (d.error || '连通测试失败'));
  });

  el('btnVerifyCompanyNow')?.addEventListener('click', async () => {
    if (!currentDetailCompany) return;
    const btn = el('btnVerifyCompanyNow');
    if (btn) btn.disabled = true;
    try {
      const res = await fetch('/api/company-check/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company: currentDetailCompany, force: false }),
      });
      const d = await res.json();
      if (d.company_check) {
        renderCompanyBadgeOnDetail(d.company_check, currentDetailCompany);
        const cur = packagesCache.find(p => p.package_id === selectedPkgId);
        if (cur) cur.company_check = d.company_check;
        showToast(d.company_check.risk_summary || '企业核查完成');
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  el('btnSaveEmailCfg')?.addEventListener('click', async () => {
    const payload = {
      notifications: {
        strategy: el('cfgNotifyStrategy').value,
        desktop_notify_enabled: el('cfgDesktopNotify').checked,
        push_preset: el('cfgPushPreset').value,
        push_webhook_url: el('cfgPushUrl').value.trim(),
        provider: 'email_smtp',
        email_preset: el('cfgEmailPreset').value,
        smtp_host: el('cfgSmtpHost').value.trim(),
        smtp_port: Number(el('cfgSmtpPort').value || 465),
        smtp_security: el('cfgSmtpSecurity').value,
        smtp_user: el('cfgSmtpUser').value.trim(),
        email_to: el('cfgEmailTo').value.trim() || el('cfgSmtpUser').value.trim(),
        smtp_pass: el('cfgSmtpPass').value.trim(),
      },
    };
    const res = await fetch('/api/system/settings', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    const d = await res.json();
    el('cfgSmtpPass').value = '';
    el('cfgPushUrl').value = '';
    showToast(res.ok ? '已保存消息提醒与备选邮箱设置' : (d.detail || '保存失败'));
    await loadSettingsPanel();
    await loadSystemStatus();
  });

  el('btnSaveRelayCfg')?.addEventListener('click', async () => {
    const prov = el('cfgRelayProvider').value;
    const payload = {
      cloud_relay: {
        enabled: prov !== 'none',
        provider: prov,
        pairing_id: el('cfgRelayPairingId').value.trim(),
        endpoint_url: el('cfgRelayEndpoint').value.trim(),
        relay_secret: el('cfgRelaySecret').value.trim(),
      },
    };
    const res = await fetch('/api/system/settings', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    const d = await res.json();
    el('cfgRelaySecret').value = '';
    showToast(res.ok ? '已保存云端加密中转接口配置' : (d.detail || '保存失败'));
    await loadSettingsPanel();
  });

  el('btnRelayPush')?.addEventListener('click', async () => {
    const res = await fetch('/api/relay/push', { method: 'POST' });
    const d = await res.json();
    const box = el('cfgRelayPreviewBox');
    if (box) {
      box.style.display = 'block';
      box.textContent =
        d.status === 'ok'
          ? `✅ 已加密推送 ${d.pushed_count} 条待审岗位至 ${d.mode}（pairing_id=${d.pairing_id}，密文 ${d.ciphertext_bytes} bytes）。`
          : `⚠️ 推送未到达云端（${d.error || d.status}），邮件兜底=${d.fallback_to_email_ready}。`;
    }
    showToast(d.status === 'ok' ? `已加密推送 ${d.pushed_count} 条待审岗位` : '云端推送触发兜底提醒');
  });

  el('btnRelayPull')?.addEventListener('click', async () => {
    const res = await fetch('/api/relay/pull', { method: 'POST' });
    const d = await res.json();
    const box = el('cfgRelayPreviewBox');
    if (box) {
      box.style.display = 'block';
      box.textContent =
        d.applied_count > 0
          ? `✅ 已解密回写 ${d.applied_count} 条手机审批决策：` + (d.applied || []).map((x) => `${x.company}·${x.title}(${x.decision})`).join('；')
          : `同步结果：${d.status}（applied=${d.applied_count || 0}）。` + (d.error ? ` 原因：${d.error}` : '');
    }
    showToast(d.applied_count > 0 ? `已回写 ${d.applied_count} 条手机端审批` : '云端暂无新的手机端审批');
    if (d.applied_count > 0) {
      await loadPackages();
      await loadApplications();
      await loadNotifications();
    }
  });

  el('btnRelayPreview')?.addEventListener('click', async () => {
    const res = await fetch('/api/relay/sync-preview', { method: 'POST' });
    const d = await res.json();
    const box = el('cfgRelayPreviewBox');
    if (box) {
      box.style.display = 'block';
      box.textContent =
        `工作模式：${d.mode}（已连云端=${d.configured}，断线邮件兜底=${d.fallback_to_email_ready}）\\n` +
        `配对标识：${d.pairing_id} · 加密条数：${d.plaintext_count} · 本地解密往返校验：${d.roundtrip_verified ? '通过' : '异常'}\\n` +
        `密文预览（云服务器仅可见此乱码）：${d.ciphertext_preview}`;
    }
    showToast('已生成 AES-256-GCM 密文打包演示');
  });

  async function triggerTestAppNotify() {
    if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
      try { await Notification.requestPermission(); } catch (_) {}
    }
    const res = await fetch('/api/notifications/test', { method: 'POST' });
    const d = await res.json();
    const chs = (d.delivered_channels || []).join(', ') || 'app_inbox';
    showToast(`已生成测试提醒（通道：${chs}）`);
    await loadNotifications();
  }
  el('btnTestAppNotify')?.addEventListener('click', triggerTestAppNotify);
  el('btnTestAppNotifyCfg')?.addEventListener('click', triggerTestAppNotify);

  el('btnMarkAllRead')?.addEventListener('click', async () => {
    await fetch('/api/notifications/read', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids: null }),
    });
    showToast('已全部标为已读');
    await loadNotifications();
  });

  el('btnTestEmail')?.addEventListener('click', async () => {
    showToast('正在发送测试邮件...');
    const res = await fetch('/api/system/test-email', { method: 'POST' });
    const d = await res.json();
    showToast(d.status === 'sent' ? `测试邮件已发出至 ${d.email_to}` : `发送状态：${d.status}`);
  });

  el('btnSaveSchedule')?.addEventListener('click', async () => {
    const res = await fetch('/api/system/schedule', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: el('cfgSchedEnabled').checked, send_time: el('cfgSchedTime').value || '16:00' }),
    });
    const d = await res.json();
    showToast(res.ok ? (d.enabled ? `已启用每日 ${d.send_time} 定时发送` : '已关闭定时') : (d.detail || '操作失败'));
    await loadSettingsPanel();
  });

  el('btnImportResume')?.addEventListener('click', async () => {
    const fileInput = el('cfgResumeFile');
    const textVal = (el('cfgResumeText').value || '').trim();
    let payload = { filename: 'resume_pasted.txt', content_text: textVal };
    if (fileInput?.files && fileInput.files.length > 0) {
      const f = fileInput.files[0];
      const buf = await f.arrayBuffer();
      const bytes = new Uint8Array(buf);
      let bin = '';
      for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
      payload = { filename: f.name, content_base64: btoa(bin) };
    }
    const res = await fetch('/api/system/import-resume', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    const d = await res.json();
    showToast(res.ok ? `简历已导入激活（${d.version_tag}，要点 ${d.bullets_count} 条）` : (d.detail || '导入失败'));
    await loadSettingsPanel();
    await loadSystemStatus();
  });

  el('btnSavePrefs')?.addEventListener('click', async () => {
    const payload = {
      profile: {
        graduation_year: Number(el('cfgProfYear').value || 2027),
        major: el('cfgProfMajor').value.trim(),
        target_roles: el('cfgTargetRoles').value,
      },
      preferences: { primary_cities: el('cfgPrimaryCities').value, excluded_keywords: el('cfgExcludedKw').value },
      scoring: { min_score_for_package: Number(el('cfgMinScore').value || 80) },
    };
    const res = await fetch('/api/system/settings', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    const d = await res.json();
    showToast(res.ok ? '已保存个人偏好与评分阈值' : (d.detail || '保存失败'));
    await loadSettingsPanel();
    updateCfExtraSummary();
    await loadPackages();
    await loadDataDashboard();
  });

  // Custom User-Defined Scoring & Filtering Rule Builder + Reference Panel
  const splitTokens = (txt) => String(txt || '').split(/[,，、;\\n]+/).map((s) => s.trim()).filter(Boolean);
  const readActiveChips = (sel, attr) => Array.from(document.querySelectorAll(sel + '.active')).map((b) => b.dataset[attr]).filter(Boolean);

  let customRulesState = [];
  let refTemplatesCache = [];

  const FIELD_OPTS = [
    ['any_text', '全部文本(公司+职位+JD)'],
    ['title', '职位名称'],
    ['company', '公司名称'],
    ['city', '工作城市'],
    ['job_type', '岗位批次(校招/实习)'],
    ['apply_channel', '投递渠道'],
    ['source', '数据来源'],
    ['factcheck_status', '核验状态'],
  ];
  const MODE_OPTS = [
    ['multi_any', '多选任一命中'],
    ['single', '单选精确匹配'],
    ['multi_all', '多选全部同时命中'],
  ];
  const ACTION_OPTS = [
    ['add', '命中加分 (+)'],
    ['deduct', '命中扣分 (-)'],
    ['require', '必须满足(硬门槛)'],
    ['exclude', '一票排除(淘汰)'],
  ];

  function renderCustomRules() {
    const box = el('cfRulesList');
    if (!box) return;
    box.replaceChildren();
    if (customRulesState.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'cf-rule-card';
      empty.style.color = '#6b7280';
      empty.style.fontSize = '12px';
      empty.textContent = '暂未添加自定义规则。点击右上角「+ 新增一条规则」，或点击右侧「➕ 套用」参考模板自由调整口碑分值。';
      box.appendChild(empty);
      return;
    }
    customRulesState.forEach((rule, idx) => {
      const card = document.createElement('div');
      card.className = 'cf-rule-card';

      const row1 = document.createElement('div');
      row1.className = 'cf-rule-row1';

      const chk = document.createElement('input');
      chk.type = 'checkbox';
      chk.checked = rule.enabled !== false;
      chk.title = '启用/暂停此条规则';
      chk.onchange = () => { rule.enabled = chk.checked; };

      const nameInp = document.createElement('input');
      nameInp.className = 'cf-inp-sm';
      nameInp.style.flex = '1';
      nameInp.style.minWidth = '130px';
      nameInp.placeholder = `规则口径名称（如 口径${idx + 1}）`;
      nameInp.value = rule.name || '';
      nameInp.oninput = () => { rule.name = nameInp.value; };

      const fieldSel = document.createElement('select');
      fieldSel.className = 'cf-inp-sm';
      FIELD_OPTS.forEach(([val, label]) => {
        const opt = document.createElement('option');
        opt.value = val;
        opt.textContent = label;
        fieldSel.appendChild(opt);
      });
      fieldSel.value = rule.field || 'any_text';
      fieldSel.onchange = () => { rule.field = fieldSel.value; };

      const modeSel = document.createElement('select');
      modeSel.className = 'cf-inp-sm';
      MODE_OPTS.forEach(([val, label]) => {
        const opt = document.createElement('option');
        opt.value = val;
        opt.textContent = label;
        modeSel.appendChild(opt);
      });
      modeSel.value = rule.match_mode || 'multi_any';
      modeSel.onchange = () => { rule.match_mode = modeSel.value; };

      const delBtn = document.createElement('button');
      delBtn.type = 'button';
      delBtn.className = 'btn btn-outline';
      delBtn.style.padding = '4px 8px';
      delBtn.style.fontSize = '11.5px';
      delBtn.style.color = '#b91c1c';
      delBtn.textContent = '删除';
      delBtn.onclick = () => {
        customRulesState.splice(idx, 1);
        renderCustomRules();
      };

      row1.append(chk, nameInp, fieldSel, modeSel, delBtn);

      const row2 = document.createElement('div');
      row2.className = 'cf-rule-row2';

      const valInp = document.createElement('input');
      valInp.className = 'cf-inp-sm';
      valInp.style.flex = '1';
      valInp.style.minWidth = '180px';
      valInp.placeholder = '输入口径取值（逗号分隔，单选写1个或多个精确值；多选写多个词）';
      valInp.value = Array.isArray(rule.values) ? rule.values.join(', ') : String(rule.values || '');
      valInp.oninput = () => { rule.values = splitTokens(valInp.value); };

      const actSel = document.createElement('select');
      actSel.className = 'cf-inp-sm';
      ACTION_OPTS.forEach(([val, label]) => {
        const opt = document.createElement('option');
        opt.value = val;
        opt.textContent = label;
        actSel.appendChild(opt);
      });
      actSel.value = rule.action || 'add';

      const scoreInp = document.createElement('input');
      scoreInp.type = 'number';
      scoreInp.min = '0';
      scoreInp.max = '200';
      scoreInp.className = 'cf-inp-sm';
      scoreInp.style.width = '72px';
      scoreInp.value = String(rule.score ?? 20);
      const syncScoreVis = () => {
        const isScoring = actSel.value === 'add' || actSel.value === 'deduct';
        scoreInp.disabled = !isScoring;
        scoreInp.style.opacity = isScoring ? '1' : '0.45';
      };
      syncScoreVis();
      actSel.onchange = () => {
        rule.action = actSel.value;
        syncScoreVis();
      };
      scoreInp.oninput = () => {
        rule.score = Math.max(0, Math.min(200, Number(scoreInp.value || 0)));
      };

      const scoreUnit = document.createElement('span');
      scoreUnit.style.fontSize = '11.5px';
      scoreUnit.style.color = '#6b7280';
      scoreUnit.textContent = '分';

      row2.append(valInp, actSel, scoreInp, scoreUnit);
      card.append(row1, row2);
      box.appendChild(card);
    });
    if (typeof updateCfExtraSummary === 'function') updateCfExtraSummary();
  }

  function renderFilterReferences() {
    const box = el('cfReferenceList');
    if (!box) return;
    box.replaceChildren();
    const fieldNameMap = Object.fromEntries(FIELD_OPTS);
    refTemplatesCache.forEach((tpl) => {
      const card = document.createElement('div');
      card.className = 'cf-ref-item';

      const hd = document.createElement('div');
      hd.className = 'cf-ref-head';
      const title = document.createElement('strong');
      title.style.fontSize = '12px';
      title.style.color = 'var(--ink)';
      title.textContent = tpl.name || '';
      const scoreBadge = document.createElement('span');
      scoreBadge.className = 'cf-ref-score';
      scoreBadge.textContent =
        tpl.action === 'exclude'
          ? '一票排除'
          : tpl.action === 'require'
            ? '必须满足'
            : tpl.action === 'deduct'
              ? `-${tpl.score} 分`
              : `+${tpl.score} 分`;
      const addBtn = document.createElement('button');
      addBtn.type = 'button';
      addBtn.className = 'cf-chip';
      addBtn.style.padding = '2px 8px';
      addBtn.style.fontSize = '11px';
      addBtn.textContent = '➕ 套用';
      addBtn.onclick = () => {
        customRulesState.push({
          id: 'rule_' + Date.now(),
          name: tpl.name,
          enabled: true,
          field: tpl.field || 'any_text',
          match_mode: tpl.match_mode || 'multi_any',
          values: [...(tpl.values || [])],
          action: tpl.action || 'add',
          score: Number(tpl.score ?? 20),
        });
        renderCustomRules();
        showToast(`已套用「${tpl.name}」到左侧，可自由修改分值与词汇`);
      };
      const rightGrp = document.createElement('div');
      rightGrp.style.display = 'flex';
      rightGrp.style.alignItems = 'center';
      rightGrp.style.gap = '5px';
      rightGrp.append(scoreBadge, addBtn);
      hd.append(title, rightGrp);

      const meta = document.createElement('div');
      meta.style.fontSize = '11px';
      meta.style.color = '#6b7280';
      meta.textContent = `${fieldNameMap[tpl.field] || tpl.field} · 示例值：${(tpl.values || []).join(', ')}`;

      const hint = document.createElement('div');
      hint.style.fontSize = '11px';
      hint.style.color = '#4b5563';
      hint.style.marginTop = '2px';
      hint.textContent = tpl.hint || '';

      card.append(hd, meta, hint);
      box.appendChild(card);
    });
  }

  el('btnAddCfRule')?.addEventListener('click', () => {
    customRulesState.push({
      id: 'rule_' + Date.now(),
      name: `自定义口径 ${customRulesState.length + 1}`,
      enabled: true,
      field: 'any_text',
      match_mode: 'multi_any',
      values: [],
      action: 'add',
      score: 20,
    });
    renderCustomRules();
  });

  el('btnLoadRefTemplate')?.addEventListener('click', () => {
    if (!refTemplatesCache.length) return;
    customRulesState = refTemplatesCache.map((tpl, i) => ({
      id: `rule_tpl_${i + 1}`,
      name: tpl.name,
      enabled: true,
      field: tpl.field || 'any_text',
      match_mode: tpl.match_mode || 'multi_any',
      values: [...(tpl.values || [])],
      action: tpl.action || 'add',
      score: Number(tpl.score ?? 20),
    }));
    if (el('cfgCfMinScore')) {
      el('cfgCfMinScore').value = '60';
      document.querySelectorAll('#cfScorePresets .cf-chip').forEach((b) => {
        b.classList.toggle('active', Number(b.dataset.cfScore) === 60);
      });
    }
    renderCustomRules();
    showToast('已一键载入全套参考模板，请按你的实际求职标准自由修改分值后保存');
  });

  document.querySelectorAll('#cfModeGroup .cf-chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#cfModeGroup .cf-chip').forEach((b) => b.classList.toggle('active', b === btn));
    });
  });

  document.querySelectorAll('#cfScorePresets .cf-chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      const val = Number(btn.dataset.cfScore || 0);
      if (el('cfgCfMinScore')) el('cfgCfMinScore').value = String(val);
      document.querySelectorAll('#cfScorePresets .cf-chip').forEach((b) => b.classList.toggle('active', b === btn));
    });
  });
  el('cfgCfMinScore')?.addEventListener('input', () => {
    const val = Number(el('cfgCfMinScore').value || 0);
    document.querySelectorAll('#cfScorePresets .cf-chip').forEach((b) => {
      b.classList.toggle('active', Number(b.dataset.cfScore) === val);
    });
  });

  function updateCfExtraSummary() {
    const sum = el('cfExtraSummary');
    if (!sum) return;
    const scope = document.querySelector('#cfCityScopeGroup .cf-chip.active')?.dataset.cfCityScope || 'all';
    const cnt =
      (scope !== 'all' ? 1 : 0) +
      readActiveChips('#cfJobTypesGroup .cf-chip', 'cfJobtype').length +
      readActiveChips('#cfFactcheckGroup .cf-chip', 'cfFact').length +
      readActiveChips('#cfChannelsGroup .cf-chip', 'cfChannel').length +
      readActiveChips('#cfSourcesGroup .cf-chip', 'cfSource').length;
    if (cnt > 0) {
      sum.textContent = `⚠️ 附加快捷限定（当前已附加 ${cnt} 项硬性限制 · 点此展开或一键清空）`;
      sum.style.color = '#b45309';
    } else {
      sum.textContent = '附加快捷限定（当前无额外硬限制，完全交由上方规则裁决）';
      sum.style.color = '#4b5563';
    }
  }

  el('btnClearCfExtra')?.addEventListener('click', () => {
    document.querySelectorAll('#cfCityScopeGroup .cf-chip').forEach((b) => {
      b.classList.toggle('active', b.dataset.cfCityScope === 'all');
    });
    if (el('cfgCfCities')) el('cfgCfCities').value = '';
    document.querySelectorAll('#cfCityChips .cf-chip').forEach((b) => b.classList.remove('active'));
    ['#cfJobTypesGroup .cf-chip', '#cfFactcheckGroup .cf-chip', '#cfChannelsGroup .cf-chip', '#cfSourcesGroup .cf-chip'].forEach((sel) => {
      document.querySelectorAll(sel).forEach((b) => b.classList.remove('active'));
    });
    updateCfExtraSummary();
    showToast('已清空附加快捷限定，点击「保存并全局启用规则」后生效');
  });

  document.querySelectorAll('#cfCityScopeGroup .cf-chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#cfCityScopeGroup .cf-chip').forEach((b) => b.classList.toggle('active', b === btn));
      updateCfExtraSummary();
    });
  });

  ['#cfJobTypesGroup .cf-chip', '#cfFactcheckGroup .cf-chip', '#cfChannelsGroup .cf-chip', '#cfSourcesGroup .cf-chip'].forEach((sel) => {
    document.querySelectorAll(sel).forEach((btn) => {
      btn.addEventListener('click', () => {
        btn.classList.toggle('active');
        updateCfExtraSummary();
      });
    });
  });

  function bindChipInputSync(chipSel, attr, inputId) {
    const inp = el(inputId);
    document.querySelectorAll(chipSel).forEach((btn) => {
      btn.addEventListener('click', () => {
        const tok = String(btn.dataset[attr] || '').trim();
        if (!tok || !inp) return;
        const cur = splitTokens(inp.value);
        const exists = cur.includes(tok);
        const next = exists ? cur.filter((x) => x !== tok) : [...cur, tok];
        inp.value = next.join(', ');
        btn.classList.toggle('active', !exists);
      });
    });
    inp?.addEventListener('input', () => {
      const picked = new Set(splitTokens(inp.value));
      document.querySelectorAll(chipSel).forEach((b) => b.classList.toggle('active', picked.has(String(b.dataset[attr] || ''))));
    });
  }
  bindChipInputSync('#cfCityChips .cf-chip', 'cfCity', 'cfgCfCities');

  function collectCustomFilterPayload(forceEnable = null) {
    const activeScope = document.querySelector('#cfCityScopeGroup .cf-chip.active')?.dataset.cfCityScope || 'all';
    const activeMode = document.querySelector('#cfModeGroup .cf-chip.active')?.dataset.cfMode || 'override';
    const enabled = forceEnable === null ? Boolean(el('cfgCfEnabled')?.checked) : Boolean(forceEnable);
    if (el('cfgCfEnabled') && forceEnable !== null) el('cfgCfEnabled').checked = Boolean(forceEnable);
    const minScore = Math.max(0, Math.min(200, Number(el('cfgCfMinScore')?.value || 0)));
    const baseScore = Math.max(0, Math.min(100, Number(el('cfgCfBaseScore')?.value || 0)));
    return {
      preferences: {
        custom_filter: {
          enabled,
          mode: activeMode,
          base_score: baseScore,
          min_display_score: minScore,
          rules: customRulesState.map((r, i) => ({
            id: r.id || `rule_${i + 1}`,
            name: r.name || `自定义口径 ${i + 1}`,
            enabled: r.enabled !== false,
            field: r.field || 'any_text',
            match_mode: r.match_mode || 'multi_any',
            values: Array.isArray(r.values) ? r.values : splitTokens(r.values),
            action: r.action || 'add',
            score: Math.max(0, Math.min(200, Number(r.score ?? 20))),
          })),
          city_scope: activeScope,
          custom_cities: splitTokens(el('cfgCfCities')?.value),
          job_types: readActiveChips('#cfJobTypesGroup .cf-chip', 'cfJobtype'),
          apply_channels: readActiveChips('#cfChannelsGroup .cf-chip', 'cfChannel'),
          factcheck_statuses: readActiveChips('#cfFactcheckGroup .cf-chip', 'cfFact'),
          sources: readActiveChips('#cfSourcesGroup .cf-chip', 'cfSource'),
          include_keywords: [],
          excluded_keywords: [],
        },
      },
    };
  }

  async function saveCustomFilter(forceEnable = null, runAfter = false) {
    const payload = collectCustomFilterPayload(forceEnable);
    const res = await fetch('/api/system/settings', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    const d = await res.json();
    if (!res.ok) {
      showToast(d.detail || '保存自定义规则失败');
      return;
    }
    const on = Boolean(payload.preferences.custom_filter.enabled);
    showToast(on ? '已保存并启用全局自定义筛选与算分规则' : '已保存规则配置（当前未启用全局接管）');
    await loadSettingsPanel();
    updateCfExtraSummary();
    await loadPackages();
    await loadDataDashboard();
    if (runAfter) {
      await triggerRunScreen();
    }
  }

  el('btnSaveCustomFilter')?.addEventListener('click', () => saveCustomFilter(true, false));
  el('btnSaveCustomFilterAndRun')?.addEventListener('click', () => saveCustomFilter(true, true));
  el('btnResetCustomFilter')?.addEventListener('click', async () => {
    customRulesState = [];
    const res = await fetch('/api/system/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        preferences: {
          custom_filter: {
            enabled: false,
            mode: 'override',
            base_score: 0,
            min_display_score: 0,
            rules: [],
            city_scope: 'all',
            custom_cities: [],
            job_types: [],
            apply_channels: [],
            factcheck_statuses: [],
            sources: [],
            include_keywords: [],
            excluded_keywords: [],
          },
        },
      }),
    });
    if (res.ok) {
      showToast('已重置为全部岗位默认放行');
      await loadSettingsPanel();
      updateCfExtraSummary();
      await loadPackages();
      await loadDataDashboard();
    }
  });
  el('cfgCfEnabled')?.addEventListener('change', () => saveCustomFilter(null, false));
  el('globalFilterBanner')?.addEventListener('click', () => {
    el('btnTopSettings')?.click();
    document.querySelector('#cfgNav [data-cfg-sec="prefs"]')?.click();
  });

  async function triggerRunScreen() {
    setCapsule(true, '正在 AI 筛选与生成单页简历...');
    showToast('正在运行预筛与 AI 智能定制 (Stage 2)...');
    try {
      const res = await fetch('/api/stage5/run-screen', { method: 'POST' });
      const d = await res.json();
      const s2 = d.steps?.stage2 || {};
      showToast(`筛选完成：新生成投递包 ${s2.packages_built || 0} 份`);
      await loadPackages();
      await loadStage5Overview();
      await loadSystemStatus();
    } finally {
      setCapsule(false);
    }
  }
  el('btnRunScreen')?.addEventListener('click', triggerRunScreen);
  el('btnSettingsRunScreen')?.addEventListener('click', triggerRunScreen);

  async function triggerLaunchBrowser() {
    showToast('正在启动/激活带采集扩展的浏览器 (CDP 9222)...');
    const res = await fetch('/api/system/launch-browser', { method: 'POST' });
    const d = await res.json();
    showToast(d.ok ? (d.status === 'already_running' ? '抓岗浏览器已在运行' : '已启动带扩展抓岗浏览器 (9222)') : (d.error || '启动失败'));
    await loadSystemStatus();
  }

  async function triggerExpandOnly() {
    setCapsule(true, '正在抓取公开岗位与接管页面...');
    try {
      const res = await fetch('/api/stage5/expand-only', { method: 'POST' });
      const d = await res.json();
      const edge = d.steps?.edge_takeover || {};
      showToast(`抓取完成（run #${d.run_id}）：新增 ${edge.tabs_inserted || 0} 条`);
      await loadPackages();
      await loadStage5Overview();
      await loadSystemStatus();
    } finally {
      setCapsule(false);
    }
  }

  el('btnLaunchBrowser')?.addEventListener('click', triggerLaunchBrowser);
  el('btnEmptyLaunchBrowser')?.addEventListener('click', triggerLaunchBrowser);
  el('btnSettingsLaunchBrowser')?.addEventListener('click', triggerLaunchBrowser);
  el('btnOneClickExpand')?.addEventListener('click', triggerExpandOnly);
  el('btnEmptyExpand')?.addEventListener('click', triggerExpandOnly);
  el('btnSettingsSeedDemo')?.addEventListener('click', triggerSeedDemo);
  const runBootstrap = async () => {
    const res = await fetch('/api/system/bootstrap', { method: 'POST' });
    const d = await res.json();
    showToast(d.created_files?.length ? `已初始化 ${d.created_files.length} 个模板` : '本地目录与数据库已就绪');
    await loadSystemStatus();
  };
  el('btnEmptyBootstrap')?.addEventListener('click', runBootstrap);
  el('btnSettingsBootstrap')?.addEventListener('click', runBootstrap);

  // Settings Category Nav & Accordion Toggle
  el('cfgNav')?.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-cfg-sec]');
    if (!btn) return;
    const sec = btn.dataset.cfgSec;
    document.querySelectorAll('#cfgNav .cfg-nav-item').forEach(b => b.classList.toggle('active', b.dataset.cfgSec === sec));
    document.querySelectorAll('.cfg-section[data-cfg-panel]').forEach(p => p.classList.toggle('active', p.dataset.cfgPanel === sec));
  });
  document.querySelectorAll('.acc-card .acc-hd').forEach(hd => {
    hd.addEventListener('click', () => {
      const card = hd.closest('.acc-card');
      if (!card) return;
      const isOpen = card.classList.toggle('open');
      const tog = hd.querySelector('.acc-toggle');
      if (tog) tog.textContent = isOpen ? '−' : '+';
    });
  });

  el('btnSendEmail')?.addEventListener('click', async () => {
    showToast('正在按「App 优先 · 邮箱备选」发送今日提醒...');
    const res = await fetch('/api/stage5/send-email', { method: 'POST' });
    const d = await res.json();
    const n = d.steps?.notification || {};
    const mail = d.steps?.email || {};
    if (n.app_notified) {
      showToast(`已发送应用内提醒（${(n.delivered_channels || []).join('+')}）`);
      await loadNotifications();
    } else if (mail.status === 'sent') {
      showToast(`已自动降级通过邮箱发送至 ${mail.email_to}`);
    } else {
      showToast(`提醒状态：${mail.status || n.strategy || 'done'}`);
    }
  });

  async function loadDataDashboard() {
    try {
      const qs = new URLSearchParams({
        source: el('dataSourceFilter')?.value || 'all',
        job_type: el('dataTypeFilter')?.value || 'all',
        status: el('dataStatusFilter')?.value || 'active',
        q: (el('dataSearchInput')?.value || '').trim(),
        only_custom_matched: el('dataOnlyCustomMatched')?.checked ? 'true' : 'false',
        limit: '120',
      });
      const res = await fetch('/api/data/jobs-dashboard?' + qs.toString());
      const d = await res.json();
      const s = d.summary || {};
      const bd = d.breakdowns || {};

      if (el('dataSummary')) {
        el('dataSummary').textContent =
          `当前账号本地库共 ${s.total_jobs || 0} 条岗位（活跃 ${s.active_jobs || 0} · 覆盖 ${s.unique_companies || 0} 家企业 · 近24h新增 ${s.recent_24h || 0}）` +
          (s.custom_filter_active ? ` · 全局规则生效：${s.custom_filter_summary || '已启用'}` : '');
      }

      const kpiBox = el('dataKpiGrid');
      if (kpiBox) {
        kpiBox.replaceChildren();
        const kpis = [
          { label: '累计抓取岗位', val: s.total_jobs || 0, sub: `含已筛除 ${s.filtered_out_jobs || 0} 条` },
          { label: '活跃有效岗位', val: s.active_jobs || 0, sub: '处于可筛选/投递池' },
          { label: '已评估 / 已出简历', val: `${s.matched_jobs || 0} / ${s.packages_count || 0}`, sub: 'AI 评分 / 一页定制 PDF' },
          { label: '覆盖企业数量', val: s.unique_companies || 0, sub: '已去重企业主体' },
          { label: '近 24 小时新抓', val: s.recent_24h || 0, sub: '本地实时同步增量' },
          {
            label: s.custom_filter_active ? '自定义规则命中' : '自定义规则状态',
            val: s.custom_filter_active ? (s.custom_passed_jobs || 0) : '未启用',
            sub: s.custom_filter_active ? '点右侧按钮可改分值口径' : '前往设置可自由配置规则',
          },
        ];
        kpis.forEach((k) => {
          const card = document.createElement('div');
          card.className = 'data-kpi-card';
          const lbl = document.createElement('div');
          lbl.className = 'data-kpi-label';
          lbl.textContent = k.label;
          const val = document.createElement('div');
          val.className = 'data-kpi-val';
          val.textContent = String(k.val);
          const sub = document.createElement('div');
          sub.className = 'data-kpi-sub';
          sub.textContent = k.sub;
          card.append(lbl, val, sub);
          kpiBox.appendChild(card);
        });
      }

      const kbBox = el('dataKanbanGrid');
      if (kbBox) {
        kbBox.replaceChildren();
        const makeBoardCard = (titleText, rows, onClickRow) => {
          const card = document.createElement('div');
          card.className = 'data-board-card';
          const hd = document.createElement('div');
          hd.className = 'data-board-title';
          const tSpan = document.createElement('span');
          tSpan.textContent = titleText;
          const cntSpan = document.createElement('span');
          cntSpan.style.fontSize = '11px';
          cntSpan.style.color = '#6b7280';
          cntSpan.textContent = `${rows.length} 项`;
          hd.append(tSpan, cntSpan);
          card.appendChild(hd);
          if (!rows.length) {
            const emp = document.createElement('div');
            emp.style.fontSize = '12px';
            emp.style.color = '#9ca3af';
            emp.textContent = '暂无统计数据';
            card.appendChild(emp);
            return card;
          }
          const maxVal = Math.max(1, ...rows.map((r) => Number(r.count || 0)));
          rows.forEach((r) => {
            const row = document.createElement('div');
            row.className = 'data-bar-row';
            if (onClickRow) row.onclick = () => onClickRow(r);
            const meta = document.createElement('div');
            meta.className = 'data-bar-meta';
            const left = document.createElement('span');
            left.textContent = r.label || r.city || r.date || r.key || '-';
            const right = document.createElement('span');
            right.style.color = '#5b21b6';
            right.textContent = r.active !== undefined && r.active !== r.count ? `${r.active}/${r.count}` : String(r.count || 0);
            meta.append(left, right);
            const track = document.createElement('div');
            track.className = 'data-bar-track';
            const fill = document.createElement('div');
            fill.className = 'data-bar-fill';
            fill.style.width = `${Math.max(4, Math.round((Number(r.count || 0) / maxVal) * 100))}%`;
            track.appendChild(fill);
            row.append(meta, track);
            card.appendChild(row);
          });
          return card;
        };

        kbBox.appendChild(
          makeBoardCard('一、来源渠道分布（点击筛选）', (bd.by_source || []).slice(0, 8), (r) => {
            if (el('dataSourceFilter')) el('dataSourceFilter').value = r.key || 'all';
            loadDataDashboard();
          })
        );
        const typeAndCh = [
          ...(bd.by_job_type || []).map((x) => ({ ...x, _kind: 'type', label: `批次 · ${x.label}` })),
          ...(bd.by_channel || []).map((x) => ({ ...x, _kind: 'channel', label: `投递 · ${x.label}` })),
        ];
        kbBox.appendChild(
          makeBoardCard('二、批次与投递渠道拆解', typeAndCh.slice(0, 8), (r) => {
            if (r._kind === 'type' && el('dataTypeFilter')) {
              el('dataTypeFilter').value = ['校招', '实习', '未知'].includes(r.key) ? r.key : 'all';
              loadDataDashboard();
            }
          })
        );
        kbBox.appendChild(
          makeBoardCard('三、热门城市覆盖 Top 8', (bd.top_cities || []).slice(0, 8), (r) => {
            if (el('dataSearchInput')) el('dataSearchInput').value = r.city || '';
            loadDataDashboard();
          })
        );
        kbBox.appendChild(
          makeBoardCard('四、每日入库趋势（近10天）', (bd.daily_trend || []).slice(-8).reverse(), null)
        );
      }

      const metaEl = el('dataJobsMeta');
      const rowsBox = el('dataJobsRows');
      const jobs = d.jobs || [];
      if (metaEl) {
        const totalMatched = Number(s.matched_query_count ?? jobs.length);
        metaEl.textContent = `全库共筛选命中 ${totalMatched} 条 · 按规则/匹配评分从高到低展示前 ${jobs.length} 条（单页上限 120 条；可按来源、批次或关键词二次钻取）`;
      }
      if (rowsBox) {
        rowsBox.replaceChildren();
        if (!jobs.length) {
          const emp = document.createElement('div');
          emp.style.padding = '18px 8px';
          emp.style.color = '#6b7280';
          emp.style.fontSize = '12.5px';
          emp.textContent = '当前筛选条件下暂无岗位记录。可点击「重置」或右上角「一键抓取新岗位」导入最新职位。';
          rowsBox.appendChild(emp);
        } else {
          jobs.forEach((j) => {
            const row = document.createElement('div');
            row.className = 'data-job-row';

            const left = document.createElement('div');
            left.style.flex = '1';
            left.style.minWidth = '240px';
            const titleLine = document.createElement('div');
            titleLine.style.fontWeight = '800';
            titleLine.style.fontSize = '13.5px';
            titleLine.style.color = 'var(--ink)';
            titleLine.textContent = `${j.company} · ${j.title}`;

            const subLine = document.createElement('div');
            subLine.style.fontSize = '11.5px';
            subLine.style.color = 'var(--muted)';
            subLine.style.marginTop = '3px';
            const cText = (j.cities || []).join('/') || '未标注城市';
            subLine.textContent =
              `${j.source_label || j.source} · ${j.job_type} · ${cText} · ${j.channel_label}` +
              (j.deadline ? ` · 截止 ${j.deadline}` : '') +
              (j.created_at ? ` · 入库 ${j.created_at.slice(0, 10)}` : '');

            left.append(titleLine, subLine);
            if (Array.isArray(j.custom_hits) && j.custom_hits.length > 0) {
              const hits = document.createElement('div');
              hits.className = 'cf-hits-line';
              j.custom_hits.forEach((ht) => {
                const tag = document.createElement('span');
                tag.className = 'cf-hit-tag';
                tag.textContent = ht;
                hits.appendChild(tag);
              });
              left.appendChild(hits);
            }

            const right = document.createElement('div');
            right.style.display = 'flex';
            right.style.gap = '6px';
            right.style.alignItems = 'center';
            right.style.flexWrap = 'wrap';

            const stPill = document.createElement('span');
            stPill.className = 'pill ' + (j.status === 'active' ? 'pill-approve' : 'pill-later');
            stPill.textContent = j.status === 'active' ? '活跃' : j.status;
            right.appendChild(stPill);

            if (j.company_check && j.company_check.risk_level && j.company_check.risk_level !== 'unknown') {
              const ccPill = document.createElement('span');
              const lvl = j.company_check.risk_level;
              ccPill.className = 'pill ' + (lvl === 'severe' ? 'pill-reject' : (lvl === 'warning' ? 'pill-later' : 'pill-approve'));
              ccPill.textContent = lvl === 'severe' ? '🚨高危' : (lvl === 'warning' ? '⚠️留意' : '🛡️存续');
              ccPill.title = j.company_check.risk_summary || '';
              right.appendChild(ccPill);
            }

            if (s.custom_filter_active) {
              const cfPill = document.createElement('span');
              cfPill.className = 'pill ' + (j.custom_passed ? 'pill-approve' : 'pill-reject');
              cfPill.textContent = j.custom_passed ? `规则 ${j.custom_score}分` : `未达线(${j.custom_score}分)`;
              right.appendChild(cfPill);
            } else if (j.match_score !== null && j.match_score !== undefined) {
              const scPill = document.createElement('span');
              scPill.className = 'score-badge';
              scPill.textContent = `AI ${j.match_score}分`;
              right.appendChild(scPill);
            }

            if (j.url && new RegExp('^https?://', 'i').test(j.url)) {
              const link = document.createElement('a');
              link.className = 'btn btn-outline';
              link.style.padding = '4px 9px';
              link.style.fontSize = '11.5px';
              link.href = j.url;
              link.target = '_blank';
              link.rel = 'noopener noreferrer';
              link.textContent = '原岗链接';
              right.appendChild(link);
            }

            row.append(left, right);
            rowsBox.appendChild(row);
          });
        }
      }
    } catch (_) {}
  }

  el('btnRefreshData')?.addEventListener('click', loadDataDashboard);
  el('btnDataApplyFilter')?.addEventListener('click', loadDataDashboard);
  el('dataSearchInput')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') loadDataDashboard(); });
  el('dataSourceFilter')?.addEventListener('change', loadDataDashboard);
  el('dataTypeFilter')?.addEventListener('change', loadDataDashboard);
  el('dataStatusFilter')?.addEventListener('change', loadDataDashboard);
  el('dataOnlyCustomMatched')?.addEventListener('change', loadDataDashboard);
  el('btnDataResetFilter')?.addEventListener('click', () => {
    if (el('dataSearchInput')) el('dataSearchInput').value = '';
    if (el('dataSourceFilter')) el('dataSourceFilter').value = 'all';
    if (el('dataTypeFilter')) el('dataTypeFilter').value = 'all';
    if (el('dataStatusFilter')) el('dataStatusFilter').value = 'active';
    if (el('dataOnlyCustomMatched')) el('dataOnlyCustomMatched').checked = false;
    loadDataDashboard();
  });
  el('btnDataJumpRules')?.addEventListener('click', () => {
    switchMainTab('settings');
    document.querySelector('#cfgNav [data-cfg-sec="prefs"]')?.click();
  });
  el('btnDataExpand')?.addEventListener('click', triggerExpandOnly);

  el('btnRefresh')?.addEventListener('click', () => {
    loadPackages(); loadApplications(); loadStage5Overview(); loadDataDashboard(); loadSystemStatus(); loadNotifications();
    showToast('已刷新全部本地数据');
  });

  // Ctrl+K Global Command Palette
  const cmdBack = el('cmdBackdrop');
  const cmdInp = el('cmdInput');
  const cmdList = el('cmdList');
  function buildCommands(query) {
    const q = (query || '').trim().toLowerCase();
    const baseCmds = [
      { label: '⚡ 一键载入示例体验数据（免 API Key）', hint: '演示模式', run: triggerSeedDemo },
      { label: '📄 打开今日待审岗位列表', hint: '审阅', run: () => switchMainTab('pdf') },
      { label: '🔔 查看消息提醒中心', hint: '消息', run: () => switchMainTab('inbox') },
      { label: '📋 切换投递追踪 / Kanban 看板', hint: '看板', run: () => switchMainTab('queue') },
      { label: '🗂️ 打开岗位数据拆解看板', hint: '数据', run: () => switchMainTab('data') },
      { label: '⚙️ 打开模型 / 邮箱 / 自定义筛选设置', hint: '设置', run: () => switchMainTab('settings') },
      { label: 'Aa 切换 120% 舒心大字关怀模式', hint: '无障碍', run: () => el('btnCareToggle').click() },
      { label: '🚀 运行 AI 智能匹配与定制简历', hint: 'AI 任务', run: triggerRunScreen },
    ];
    const pkgCmds = packagesCache.slice(0, 12).map(p => ({
      label: `岗位：${p.company} · ${p.title}`,
      hint: `${p.score}分 · ${trackText(p.job_type)}`,
      run: () => { switchMainTab('pdf'); selectPackage(p.package_id); },
    }));
    const all = [...baseCmds, ...pkgCmds].filter(c => !q || c.label.toLowerCase().includes(q) || c.hint.toLowerCase().includes(q));
    cmdList.replaceChildren();
    all.slice(0, 10).forEach(item => {
      const div = document.createElement('div');
      div.className = 'cmd-item';
      div.innerHTML = `<span>${item.label}</span><span style="color:#6b7280;font-size:11.5px;">${item.hint}</span>`;
      div.onclick = () => { closeCmd(); item.run(); };
      cmdList.appendChild(div);
    });
  }
  function openCmd() {
    cmdBack.classList.add('open');
    cmdInp.value = '';
    buildCommands('');
    setTimeout(() => cmdInp.focus(), 30);
  }
  function closeCmd() { cmdBack.classList.remove('open'); }
  el('btnCmdOpen')?.addEventListener('click', openCmd);
  el('btnOpenCmdTop')?.addEventListener('click', openCmd);
  cmdInp?.addEventListener('input', (e) => buildCommands(e.target.value));
  cmdBack?.addEventListener('click', (e) => { if (e.target === cmdBack) closeCmd(); });
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      if (cmdBack.classList.contains('open')) closeCmd(); else openCmd();
    } else if (e.key === 'Escape' && cmdBack.classList.contains('open')) {
      closeCmd();
    }
  });

  loadPackages();
  loadApplications();
  loadStage5Overview();
  loadDataDashboard();
  loadSystemStatus();
  loadNotifications();
  loadSettingsPanel();
  setInterval(loadNotifications, 30000);
  if (window.location.hash === '#settings') switchMainTab('settings');
  else if (window.location.hash === '#inbox' || window.location.hash === '#messages') switchMainTab('inbox');
  else if (window.location.hash === '#queue') switchMainTab('queue');
  else if (window.location.hash === '#insights') switchMainTab('insights');
  else if (window.location.hash === '#data') switchMainTab('data');
  else if (window.location.hash === '#detail') switchMainTab('pdf');
})();
</script>
</body>
</html>
"""
