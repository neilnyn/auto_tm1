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
models/                          ← tm1-model-builder 的 delivery 和 datasource 根目录
├── <model_summary>/             ← 当前开发模型的子目录（名称为模型简要描述，如 "Sales_Planning"）
│   ├── Account_dimension-spec.json    ← 维度 spec（供用户审查 + create_dimension_file 数据源）
│   ├── Period_dimension-spec.json
│   └── Sales_Cube_cube-spec.json      ← Cube spec（供用户审查）
```

- `models/` 是项目根目录下的固定目录，所有模型的 spec 文件都在此交付
- `<model_summary>` 是一个简短的、能描述当前模型用途的目录名（英文、下划线分隔），在 Phase 2 中与用户确认
- spec 文件既供用户审查（Human-in-the-loop），也作为 MCP 工具（如 `create_dimension_file`）的数据源

## Workflow

### Phase 1: Understand

Explore the existing TM1 model using read-only MCP tools. Use subagent (`tm1-explorer`) for multi-step exploration.

#### 使用 subagent 注意事项

- 如果 `tm1-explorer` subagent 返回了 error message，请向用户报告，不要让 subagent 自行修复

#### 探索效率原则

- **精确优先** — 用户已提供精确名称时，直接 `get_cube` / `get_dimension_info`，不要先用 `list_*` 模糊搜索
- **信息充分即停** — 已获取的信息足以完成 spec 设计时，立即停止探索。典型充分条件：Dimension 的元素结构和层级关系、Cube 的维度顺序、已有 Subset / View 结构

Clarify with the user:
- What to build (dimensions, cubes, data, or full model)
- Source of truth (spec file, user description, existing model to replicate)
- Verification criteria
- **Model summary name** — 用于 `models/` 下的子目录名（如 `Sales_Planning`、`HR_Budget`）

### Phase 2: Spec（设计 + 交付 spec 文件）

Present a build plan:
1. Dimensions to create (elements, hierarchies, attributes, subsets)
2. Cubes to create (dimension order)
3. Views to create (MDX queries)
4. Data to write (source and method)
5. Verification checkpoints

Read the spec templates for reference:
- `.claude/skills/tm1-model-builder/templates/dimension-spec.json` — dimension structure schema (elements, edges, attributes, subsets)
- `.claude/skills/tm1-model-builder/templates/cube-spec.json` — cube structure schema (dimensions, views, seed data, verify)

#### 交付 spec 文件（must-have）

用户确认方案后，按以下步骤生成 dimension和cube的spec 文件：

**Step 1** `models/<model_summary>/` - 这是 spec 文件的**唯一交付位置**。不要将 spec 文件写到项目根目录、outputs/、或其他任何位置,生成 spec JSON 文件到 `models/<model_summary>/` 下：

```
models/<model_summary>/
├── <dimension_name>_dimension-spec.json     ← 每个维度一个文件
├── <another_dim>_dimension-spec.json
└── <cube_name>_cube-spec.json               ← 每个 Cube 一个文件
```

文件命名规则：
- 维度：`<dimension_name>_dimension-spec.json`（如 `Account_dimension-spec.json`）
- Cube：`<cube_name>_cube-spec.json`（如 `Sales_Cube_cube-spec.json`）

每个 spec 文件必须严格遵循对应模板的结构（包含 `_spec_to_mcp_mapping` 字段），因为这些文件将直接作为 MCP 工具的输入。

**Step 2** — 自检：确认所有 spec 文件都位于 `models/<model_summary>/` 目录下。如果发现文件被写到了其他位置，立即移动到正确位置。

#### Human-in-the-loop 检查点（由 hook 强制执行）

本项目配置了 `spec_review_gate` hook（`scripts/hooks/spec_review_gate.py`），会在以下 MCP 写入工具被调用时自动检查：
`create_dimension_file`, `create_dimension`, `create_cube`, `create_subset`, `create_view`, `write_bulk`, `write_cell`, `write_file`

**执行流程（严格按顺序）：**

1. **展示 spec 文件** — 调用 `AskUserQuestion`，将 `models/<model_summary>/` 下所有 spec 文件的核心内容展示给用户，询问："以上 spec 文件是否正确？是否需要修改？"
2. **等待用户确认** — 用户确认无误后
3. **创建审查标记** — 在 `models/<model_summary>/` 下创建空的 `.reviewed` 文件：
   ```bash
   touch models/<model_summary>/.reviewed
   ```
   这会解除 hook 对 MCP 写入工具的拦截
4. **进入 Build 阶段**

**重要**：如果不完成步骤 1-3 直接调用 MCP 写入工具，hook 会硬拦截并返回错误消息。spec 文件被修改后（时间戳比 `.reviewed` 新），hook 会重新拦截，需要再次走审查流程。

### Phase 3: Build（基于 spec 文件执行）

Execute in dependency order: **dimensions → subsets → cubes → views → data**

#### 从 spec 文件构建

**优先使用 `create_dimension_file` 工具**，直接传入 spec 文件的项目相对路径：

```
create_dimension_file(
    instance="Neil",
    file_path="models/Sales_Planning/Account_dimension-spec.json"
)
```

这样做的好处：
- spec 文件作为单一数据源（spec 即是交付物，也是 MCP 工具输入）
- 避免在 MCP 工具调用中内联大量 JSON（payload 体积无限制）
- 用户可以脱离 Claude Code 直接修改 spec 文件后重新部署

对于 Cube spec，按 `_spec_to_mcp_mapping.execution_order` 中的步骤，使用对应的 MCP 工具逐步执行（`create_cube` → `create_view` → `write_bulk`/`write_cell` → `verify_cube`）。

Before modifying existing dimensions, run impact analysis:
```
find_cubes_by_dimension(instance=..., dimension_name="TargetDim")
# Check which cubes will be affected
get_cube_rules(instance=..., cube_name="AffectedCube")
# Check if rules reference elements being changed
```

### Phase 4: Verify（must-have）

After each major phase, run verification tools:
- `verify_dimension` — element counts, hierarchy integrity, attribute coverage
- `verify_cube` — dimension order, existence, data presence

Surface discrepancies immediately. Do not proceed to the next phase if verification fails.

### Phase 5: Hand off

If TI business logic is needed, summarize what was built and hand off to `tm1-process-writer` skill.

#### Hand-off Protocol

1. **Generate a hand-off summary** using this template (present to user and confirm):
   ```
   ## Model Build Summary for TI Development

   ### Model Spec Files
   - models/<model_summary>/ — 所有 spec 文件所在目录

   ### Cubes Built
   - [CubeName]: dimensions = [Dim1, Dim2, ...], rules = (none / existing rules text)

   ### Subsets Created
   - [DimName].[SubsetName] (static/dynamic): purpose
   - ...

   ### Seed Data Written
   - [CubeName]: N cells via write_bulk

   ### What TI Should Automate
   - [Description of recurring data loads, dimension updates, or calculations needed]

   ### TM1 Instance
   - Instance: [instance name used during build]
   ```

2. **User confirms** the summary is correct and describes the TI requirements.

3. **Transition**: Tell the user to invoke the process-writer skill:
   > "Model structure is ready. To build the TI process for [description], please use the `tm1-process-writer` skill. The summary above provides all the context needed."


## Key Rules

- **spec 文件是单一数据源** — `models/<model_summary>/` 下的 spec JSON 文件既是交付物（供审查），也是 MCP 工具的输入数据源。始终优先使用 `create_dimension_file(file_path=...)` 而非内联 JSON
- `create_dimension` accepts elements and edges in one call — prefer this over creating empty dimension then adding elements separately（当不使用 spec 文件时）
- All delete/clear tools carry `destructiveHint` — Claude Code will prompt for confirmation automatically
- Spec 文件路径使用**项目相对路径**（如 `models/Sales_Planning/Account_dimension-spec.json`），MCP 工具的 `file_path` 参数接受这种格式
