# Prompts & Schemas（Google AI Studio ↔ Antigravity 交接总线）

本目录是**双核开发工作流**的核心交接界面：

- **Google AI Studio（调优核）**：在浏览器中测试不同模型（`gemini-3.8-flash`、`gemini-4-argon`）、调试 System Instruction、验证 Structured Output JSON Schema，对 5–10 条脱敏财务校招 JD 观察打分与改写质量。
- **Antigravity（工程核）**：不把提示词和 Schema 硬编码在 Python 文件中，而是统一从本目录加载 `system.md` 与 `schema.json`，并将 `prompt_version` 写入 SQLite 便于回归对比。

## 目录结构

| 任务目录 | 用途 | 核心产出 |
|---|---|---|
| `job_match/` | M3 岗位打分与匹配策略 | `score`, `reasons[]`, `gaps[]`, `strategy` |
| `resume_tailor/` | M4 简历要点排序与保真改写 | `selected[{id, rewritten}]`, `summary` |
| `jd_split/` | M2 汇总推文/长文本拆分多条 JD | `jobs[]`（单条结构化 JD 列表） |

## 同步流程

在 AI Studio 调试完新版本后，使用 `/ai-studio-sync`（对应 `.agents/skills/ai-studio-sync/SKILL.md`）同步到本目录并跑本地回归评测。
