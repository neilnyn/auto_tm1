---
name: tm1-model-builder
description: >
  TM1 模型结构构建、数据填充与验证 — 维度、Cube、View、Subset 和数据。
  当用户需要创建维度或层级结构、建 Cube、往 TM1 中灌入/清除数据、创建 Subset 或 View、验证模型结构、
  搭建新的规划模型骨架时使用此 skill。触发短语：「创建维度」「建 cube」「灌数据」「初始化模型」
  「种子数据」「模型骨架」「搭建结构」「验证维度」「创建 subset」「创建 view」，以及任何涉及
  TM1 元数据构建而非 TI Process 逻辑编写的任务。一次性数据填充（seed data）归此 skill；
  定时/自动化的 ETL 数据加载归 tm1-process-writer。不要用于 TI Process 开发——请用
  tm1-process-writer。Also triggers on: "create dimension", "build cube", "load seed data",
  "set up model", "model skeleton", "verify cube structure", or constructing TM1 metadata.
---

# TM1 Model Builder

## 工作目录约定

```
models/                          ← spec 文件交付根目录
├── <model_summary>/             ← 当前模型子目录（如 "Sales_Planning"）
│   ├── Account_dimension-spec.json    ← 维度 spec（供审查 + create_dimension_file 输入）
│   ├── Period_dimension-spec.json
│   └── Sales_Cube_cube-spec.json      ← Cube spec（供审查）
```

- `models/` 是项目根目录下的固定目录，所有 spec 文件在此交付
- `<model_summary>` 是简短的子目录名，在 Phase 1 中与用户确认
- spec 文件既是 Human-in-the-loop 审查对象，也是 MCP 工具的数据源输入

## Workflow

### Phase 1: Understand

**1. 明确构建目标**

Clarify with the user:
- 要建什么（dimensions、cubes、data、还是完整模型）
- 数据来源（spec 文件、用户描述、复用已有模型）
- **Model summary name** — 用于 `models/` 下的子目录名（如 `Sales_Planning`、`HR_Budget`）

**2. 自评估探索需求**

在调用任何 MCP 探索工具之前，先问自己：

> **"基于当前已知信息，我能否直接设计出完整的 spec 文件？"**

- 如果**能** → 跳过探索，直接进入 Phase 2
- 如果**不能** → 列出你具体缺少什么信息才能完成设计，然后用最少的 MCP 调用去获取。每获取一项后重新评估：现在能设计了吗？

常见的设计必要信息（仅供参考，按需获取）：
- Dimension 的元素结构和层级关系
- Cube 的维度顺序
- 已有 Subset / View 结构（如果是在现有模型上扩展）
- 已有元素的属性值（如果新 spec 需要兼容）

**3. 探索执行方式**

- **1-2 个精确查询**：直接调用 MCP 工具（如 `get_cube`、`get_dimension_info`）
- **3+ 个连续查询**：委托 `tm1-explorer` subagent（`Agent(subagent_type="tm1-explorer")`）
- 如果 tm1-explorer 返回 error → 标记出来让用户处理，不要让 subagent 自行修复

### Phase 2: Spec（设计 + 交付 spec 文件）

**1. 展示构建方案**

Present a build plan:
- Dimensions to create (elements, hierarchies, attributes, subsets)
- Cubes to create (dimension order)
- Views to create (MDX queries)
- Data to write (source and method)
- Verification checkpoints

Read the spec templates for reference:
- `.claude/skills/tm1-model-builder/templates/dimension-spec.json` — dimension 结构 schema
- `.claude/skills/tm1-model-builder/templates/cube-spec.json` — cube 结构 schema

**2. 注册工作项目**（先于一切 MCP 写入操作）：
```bash
: cc-workon models/<model_summary>
```

**3. 生成 spec 文件**

在 `models/<model_summary>/` 下生成 spec JSON 文件：
```
models/<model_summary>/
├── <dimension_name>_dimension-spec.json     ← 每个维度一个文件
├── <another_dim>_dimension-spec.json
└── <cube_name>_cube-spec.json               ← 每个 Cube 一个文件
```

每个 spec 文件必须严格遵循对应模板的结构（包含 `_spec_to_mcp_mapping` 字段），因为这些文件将直接作为 MCP 工具的输入。

**4. 自检**：确认所有 spec 文件都位于 `models/<model_summary>/` 目录下。

**5. Human-in-the-loop 审查（由 spec_gate hook 强制执行）**

本项目配置了 `spec_gate` hook，所有 MCP 写入工具需要 session 绑定和审查标记。

流程：
1. 展示 spec 文件 → 调用 `AskUserQuestion` 展示所有文件内容，询问是否正确
2. 用户确认后 → 创建审查标记：`touch models/<model_summary>/.reviewed`
3. 进入 Build 阶段

未完成步骤 1-2 直接调用 MCP 写入工具会被 hook 拦截。spec 文件被修改后（时间戳比 `.reviewed` 新）需重新审查。

### Phase 3: Build（基于 spec 文件执行）

Execute in dependency order: **dimensions → subsets → cubes → views → data**

**优先使用 `create_dimension_file` 工具**，直接传入 spec 文件的项目相对路径：
```
create_dimension_file(instance="Neil", file_path="models/Sales_Planning/Account_dimension-spec.json")
```

这样做的好处：spec 文件是单一数据源（既供审查也供部署）、避免内联大 JSON、用户可脱离 Claude Code 直接修改 spec 后重新部署。

对于 Cube spec，按 `_spec_to_mcp_mapping.execution_order` 中的步骤，使用对应 MCP 工具逐步执行（`create_cube` → `create_view` → `write_bulk`/`write_cell` → `verify_cube`）。

Before modifying existing dimensions, run impact analysis:
```
find_cubes_by_dimension(instance=..., dimension_name="TargetDim")
get_cube_rules(instance=..., cube_name="AffectedCube")
```

### Phase 4: Verify

After each major phase, run verification tools:
- `verify_dimension` — element counts, hierarchy integrity, attribute coverage
- `verify_cube` — dimension order, existence, data presence

Surface discrepancies immediately. Do not proceed if verification fails.

### Phase 5: Hand off

If TI business logic is needed, generate a hand-off summary for `tm1-process-writer` skill:

```
## Model Build Summary for TI Development

### Model Spec Files
- models/<model_summary>/ — 所有 spec 文件所在目录

### Cubes Built
- [CubeName]: dimensions = [Dim1, Dim2, ...], rules = (none / existing rules text)

### Seed Data Written
- [CubeName]: brief description of data written

### What TI Should Automate
- [Description of recurring data loads, dimension updates, or calculations needed]

### TM1 Instance
- Instance: [instance name used during build]
```

Present to user for confirmation, then tell them to invoke `tm1-process-writer` skill with this summary.

## Key Rules

- **spec 文件是单一数据源** — 始终优先使用 `create_dimension_file(file_path=...)` 而非内联 JSON
- `create_dimension` accepts elements and edges in one call — prefer this over creating empty dimension then adding elements separately（当不使用 spec 文件时）
- All delete/clear tools carry `destructiveHint` — Claude Code will prompt for confirmation automatically
- Spec 文件路径使用**项目相对路径**（如 `models/Sales_Planning/Account_dimension-spec.json`）
