# CLAUDE.md

## Project Overview

Auto_TM1 uses Claude Code to automate IBM TM1 (Planning Analytics) development — building model structures (dimensions, cubes, views, subsets, data) and creating TurboIntegrator (TI) processes. It provides a TM1 MCP Server that lets Claude Code explore live TM1 instances and deploy changes directly.

## Architecture

```
Claude Code  ←stdio→  tm1_mcp_server/tm1_mcp_tool.py  (FastMCP tool definitions)
                              │
                       tm1_mcp_server/tm1_connector.py  (TM1Manager class — all TM1 logic)
                              │
                         TM1py / TM1 REST API  →  TM1 Server
```

- **tm1_mcp_tool.py** — FastMCP server entry point, auto-started by Claude Code via `.mcp.json`.
- **tm1_connector.py** — `TM1Manager` class: connection lifecycle, config loading from `config/tm1py_config.ini`, all TM1 read/write operations.
- **.claude/skills/tm1-process-writer/** — TI code templates and reference docs (coding conventions, TI function reference).
- **.claude/skills/tm1-model-builder/** — Spec templates for dimension/cube creation.

## Skill Selection Guide

| Task | Skill |
|------|-------|
| Create dimensions/hierarchies, build cubes, load seed data, set up subsets/views, verify model structure | **tm1-model-builder** |
| Develop TI processes (Prolog/Metadata/Data/Epilog), ETL logic, scheduled data loads, debug existing processes | **tm1-process-writer** |

**Cross-skill hand-off**: When model-builder finishes and the model needs TI automation, generate a "Model Build Summary for TI Development" (cube names, dimension order, subsets, seed data, what TI should automate, instance name). The user includes this summary when invoking process-writer, so the next session has full context without re-exploring.

**Concurrent needs**: If a task requires both skills, complete model-builder first, then hand off to process-writer. Do not interleave.

## Rules

- **Always plan first**: 无论用户主动使用 plan 模式，还是你通过 Agent tool 委派 planner subagent 创建计划，plan mode 内按内置机制完成计划内容，然后调用 ExitPlanMode 提交审批。用户批准后，**实现阶段的第一步**必须是将计划内容持久化到 `plans/<descriptive-name>.md`（从 `~/.claude/plans/` 读取已批准的计划内容并写入项目 `plans/` 目录），然后再开始任何实际实现工作
- **Ask user**: Plan 阶段不要自行假设或推测信息。遇到不确定的需求、 ambiguous 的描述、或缺少的关键上下文时，大胆用 AskUserQuestion 向用户确认，而不是凭猜测推进。宁可多问一句，也不要基于错误假设产出无效方案。
- **TM1 exploration**: Always use targeted queries with filters — e.g. list_cubes(filter="APQ"),get_dimension_info(dimension_name="Account"). Never do full-instance scans (listing all dims/cubes/processes without a filter) unless the user explicitly asks for it.
- **tm1 explorer**: For multi-step TM1 exploration always use `Agent` tool with `subagent_type="tm1-explorer"` to avoid context explosion
- **TI code review**: After generating any TI Process code, always run `Agent` tool with `subagent_type="ti-code-reviewer"` before presenting code to the user
- **TI scripts execute server-side** — never use local system commands in TI code
- **Credentials**: `config/tm1py_config.ini` contains TM1 server credentials — never commit to git
- **Windows environment** — use forward slashes in paths within bash, backslashes may appear in Python paths
- **Python runtime**: Use `.venv/Scripts/python.exe` when running Python commands
- **Plan agent skill 传递**: 当通过 Agent tool 委派 Plan subagent 时，必须在 prompt 中主动携带相关 skill 信息（skill 名称、触发条件、适用场景），因为 subagent 无法看到父对话中 system-reminder 里的 skill 描述。具体做法：在委派 prompt 中加入"Available skills"段落，列出与当前任务相关的 skill 名称、用途和触发短语，以便 Plan agent 在规划中正确引用 skill 并按 skill 能力边界拆分任务步骤。
- **cc-workon（spec-driven 工作流必须）**: 本项目使用 spec-driven 工作流，所有 TM1 MCP 写入/破坏性工具都受 hook 拦截（`hooks/spec_review_gate.py`）。**在开始处理任何 TM1 项目开发前，必须先注册当前工作项目**，执行以下命令：
  ```
  : cc-workon models/<model_summary>
  : cc-workon processes/<process_name>
  ```
  这个命令会通过 hook 将当前 session 与目标项目目录绑定。未注册时，所有 MCP 写入工具都会被阻塞。注册后，hook 仅对你绑定的项目目录进行 spec 审查（多 session 开发时互不干扰）。详细规则：
  - 注册后 hook 会检查项目目录内的 spec 文件和 `.reviewed` 标记
  - spec 文件必须经过用户审查，审查通过后在项目目录创建 `.reviewed` 标记
  - 如为临时/improvising 操作，经用户确认后创建 `.spec_bypass` 标记
  - 只读 MCP 工具（get_*, list_*, verify_*, execute_mdx 等）不受任何限制
