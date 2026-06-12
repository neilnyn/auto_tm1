# CLAUDE.md

## Project Overview

Auto_TM1 uses Claude Code to automate IBM TM1 (Planning Analytics) development — building model structures (dimensions, cubes, views, subsets, data) and creating TurboIntegrator (TI) processes. It provides a TM1 MCP Server that lets Claude Code explore live TM1 instances and deploy changes directly.

## Project Structure

- **tm1_mcp_server** — FastMCP server entry point, auto-started by Claude Code via `.mcp.json`.
- **.claude/skills/** — Claude Code skills for TM1 development including model building and TI writing.
- **hooks/** — Spec-driven workflow hooks (spec gate, session cleanup).
- **plans/** — Plan files for task planning and execution.
- **models/** — Delivery files for TM1 model building.
- **processes/** — Delivery files for TM1 process development.

## Skill Selection Guide

| Task | Skill |
|------|-------|
| Create dimensions/hierarchies, build cubes, load seed data, set up subsets/views, verify model structure | **tm1-model-builder** |
| Develop TI processes (Prolog/Metadata/Data/Epilog), ETL logic, scheduled data loads, debug existing processes | **tm1-process-writer** |

**Cross-skill hand-off**: When model-builder finishes and the model needs TI automation, generate a "Model Build Summary for TI Development" (cube names, dimension order, subsets, seed data, what TI should automate, instance name). The user includes this summary when invoking process-writer, so the next session has full context without re-exploring.

**Concurrent needs**: If a task requires both skills, complete model-builder first, then hand off to process-writer. Do not interleave.

## Rules

- **Always plan first**: 无论用户主动使用 plan 模式，还是你通过 Agent tool 委派 planner subagent 创建计划，plan mode 内按内置机制完成计划内容，然后调用 ExitPlanMode 提交审批。用户批准后，**实现阶段的第一步**必须是将计划内容持久化到 `plans/<descriptive-name>.md`（从 `~/.claude/plans/` 读取已批准的计划内容并写入项目 `plans/` 目录），然后再开始任何实际实现工作.
- **Plan agent skill 传递**: 当通过 Agent tool 委派 Plan subagent 时，必须在 prompt 中主动携带相关 skill 信息（skill 名称、触发条件、适用场景），因为 subagent 无法看到父对话中 system-reminder 里的 skill 描述。具体做法：在委派 prompt 中加入"Available skills"段落，列出与当前任务相关的 skill 名称、用途和触发短语，以便 Plan agent 在规划中正确引用 skill 并按 skill 能力边界拆分任务步骤.
- **Ask user**: Plan 阶段不要自行假设或推测信息。遇到不确定的需求、 ambiguous 的描述、或缺少的关键上下文时，大胆用 AskUserQuestion 向用户确认，而不是凭猜测推进。宁可多问一句，也不要基于错误假设产出无效方案.
- **TM1 探索原则**: 先问自己"基于已知信息，我能不能直接开始设计？"再决定是否探索。探索时使用精确查询（带 filter），多步探索委托 `tm1-explorer` subagent（`Agent(subagent_type="tm1-explorer")`）避免上下文爆炸。两个 skill 内有更详细的探索指导。
- **TI Process 守则**: 生成 TI 代码后必须通过 `ti-code-reviewer` subagent 审查再提交用户。
- **cc-workon（spec-driven 工作流）**: 所有 TM1 MCP 写入工具受 `hooks/spec_gate.py` 拦截。开发前必须使用Bash工具先注册：`: cc-workon models/<model_summary>` 或 `: cc-workon processes/<process_name>`。注意cc-workon前面的冒号。注册后需完成 spec 审查（创建 `.reviewed` 标记）才能调用写入工具。临时操作经用户确认可创建 `.spec_bypass`。每轮对话结束绑定自动清除，新一轮需重新注册。只读 MCP 工具不受限制。
- **Python runtime**: Use `.venv/Scripts/python.exe` when running Python commands
