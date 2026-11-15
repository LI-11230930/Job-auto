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

    <!-- Independent Page 5: Settings (Left Category Nav + Right Accordion Cards) -->
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
    ['inbox', 'queue', 'insights', 'settings'].forEach(p => {
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

      const cr = d.cloud_relay || {};
      if (el('cfgRelayProvider')) {
        el('cfgRelayProvider').value = cr.provider || 'none';
        el('cfgRelayPairingId').value = cr.pairing_id || 'demo-pair-local';
        el('cfgRelayEndpoint').value = cr.endpoint_url || '';
        el('cfgRelaySecretState').textContent = cr.relay_secret_set
          ? `已配置端到端配对口令：${cr.relay_secret_masked}`
          : '未设置口令（演示时自动生成本机临时密钥，不会上传云端）';
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

  el('btnRefresh')?.addEventListener('click', () => {
    loadPackages(); loadApplications(); loadStage5Overview(); loadSystemStatus(); loadNotifications();
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
      { label: '⚙️ 打开模型 / 邮箱 / 云中转接口设置', hint: '设置', run: () => switchMainTab('settings') },
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
  loadSystemStatus();
  loadNotifications();
  loadSettingsPanel();
  setInterval(loadNotifications, 30000);
  if (window.location.hash === '#settings') switchMainTab('settings');
  else if (window.location.hash === '#inbox' || window.location.hash === '#messages') switchMainTab('inbox');
  else if (window.location.hash === '#queue') switchMainTab('queue');
  else if (window.location.hash === '#insights') switchMainTab('insights');
  else if (window.location.hash === '#detail') switchMainTab('pdf');
})();
</script>
</body>
</html>
"""
