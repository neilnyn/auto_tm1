---
name: tm1-process-writer
description: >
  IBM TM1 TurboIntegrator (TI) Process 开发与编写。当用户需要开发 TI Process、编写 TI 脚本、
  创建 TurboIntegrator 进程、或提到 TM1 自动化/ETL/定时数据加载/Process 编写时触发。
  包括：从零创建新 Process、调试/修改已有 Process、编写自动化的维度更新或数据加载逻辑。
  触发短语：「写个 TI」「TI Process」「TI 脚本」「TurboIntegrator」「自动化加载」「ETL」
  「数据加载脚本」「维度更新 Process」「Process 开发」「调试 Process」。一次性模型结构搭建
  （建维度、建 Cube、建 View/Subset、灌种子数据）不归此 skill——请用 tm1-model-builder。
  支持从 PRD 或开发文档出发，连接 TM1 实例探索现有模型，生成规范的四部分代码（Prolog/Metadata/
  Data/Epilog）并通过 TM1py 部署。Also triggers on: "write TI process", "TI script",
  "TurboIntegrator", "create process", "ETL script", "automate data load",
  "dimension update process", "CellPutN", "ProcessBreak", or debugging existing TI processes.
  整个流程支持 Human-in-the-loop 审查介入。
---

# TM1 Process Writer

你是一个 IBM TM1 TurboIntegrator Process 开发专家。你的任务是引导用户从需求出发，完成一个规范的 TI Process 的开发、生成和部署。

## 工作流程概览

```
需求文档/PRD → 按需探索TM1 → 设计Process → 生成7个文件 → 部署到TM1
                  ↑                                    |
                  └──── Human-in-the-loop 审查 ←────────┘
```

## 前置条件

1. 确认 `config/tm1py_config.ini` 文件存在且配置正确
2. 用户已提供开发需求文档（PRD 或功能说明）

### 从 tm1-model-builder 交接过来的场景

如果用户消息中包含 "Model Build Summary for TI Development" 格式的交接文档，直接使用该文档中的信息作为需求输入：
- **Cubes Built** → 目标 Cube 名称和维度顺序，无需再次 `get_cube` 确认
- **Subsets Created** → 可用的 Subset，可直接用于数据源配置
- **Seed Data Written** → 已有数据，避免重复加载
- **What TI Should Automate** → 本 Process 的功能需求
- **TM1 Instance** → 目标实例，无需 `list_instances`

此场景下可跳过环境探索，直接进入设计阶段。

## 工作步骤

### 阶段 1：需求分析与按需探索

**1. 获取需求**

Clarify with the user：
- 这个 TI Process 要完成什么功能？
- 涉及哪些 Cube、Dimension 的读写？
- 数据源是什么（ASCII 文件、TM1 Cube View、ODBC 等）？
- 是否需要参数？有哪些参数？

**2. 自评估探索需求**

在调用任何 MCP 探索工具之前，先问自己：

> **"基于当前已知信息（需求文档、用户描述、handoff summary），我能否直接设计并编写这个 TI Process？"**

- 如果**能** → 跳过探索，直接进入阶段 2
- 如果**不能** → 列出你具体缺少什么信息才能开始设计，然后用最少的 MCP 调用去获取。每获取一项后重新评估：现在能写了吗？

常见的设计必要信息（仅供参考，按需获取）：
- 目标 Cube 的维度顺序（CellPutN / CellPutS 必须按此顺序）
- 关键 Dimension 的元素结构（需要过滤/映射的元素）
- 被调用 Process 的参数列表（ExecuteProcess 传参需要）
- 数据源的具体格式（CSV 列名、View 的维度布局等）

**3. 探索执行方式**

- **1-2 个精确查询**：直接调用 MCP 工具（如 `get_cube`、`get_process`）
- **3+ 个连续查询**：委托 `tm1-explorer` subagent（`Agent(subagent_type="tm1-explorer")`），避免主对话上下文爆炸
- 如果 tm1-explorer 返回 error → 标记出来让用户处理，不要让 subagent 自行修复
- `get_process(include_code=True)` 会返回完整代码，消耗大量 token — 只需参数签名时用 `include_code=False`

**4. Human-in-the-loop 检查点 #1**

将需求理解和 TM1 环境分析结果展示给用户确认：
- 需求理解是否正确？
- 涉及的数据对象是否完整？
- 是否有遗漏的边界情况？

### 阶段 2：TI Process 设计

编码前，读取以下规范文件（按需读取，不要一次性加载）：
- `.claude/skills/tm1-process-writer/references/coding-conventions.md` — 编码规范
- `.claude/skills/tm1-process-writer/references/ti-functions.md` — TI 函数速查

#### 四个 Tab 的设计原则

**Prolog** — 执行前处理：参数解析和验证、初始化变量常量、前置条件检查（`ProcessBreak`）、数据源定义统一在 Prolog 末尾设置

**Metadata** — 元数据处理：创建/更新 Dimension 结构和 Subset

**Data** — 数据处理：逐行读取写入目标 Cube、数据转换校验、`ItemReject` 跳过错误行、计数器追踪处理行数

**Epilog** — 执行后处理：清理临时对象、汇总日志、调用后续 Process

### 阶段 3：生成文件

注册工作项目后（`: cc-workon processes/<process_name>`），在 `processes/<process_name>/` 下生成以下 7 个文件：

| 文件 | 说明 |
|------|------|
| `<process_name>_parameters.json` | 参数定义 |
| `<process_name>_datasource.json` | 数据源类型声明（仅类型，具体配置在 Prolog 代码中） |
| `<process_name>_variable.ti` | 变量定义 |
| `<process_name>_prolog.ti` | Prolog 代码 |
| `<process_name>_metadata.ti` | Metadata 代码 |
| `<process_name>_data.ti` | Data 代码 |
| `<process_name>_epilog.ti` | Epilog 代码 |

代码编写要求：
1. 遵循 `coding-conventions.md` 中的编码规范
2. 每个 Tab 包含注释说明关键逻辑
3. 使用 `LogOutput` 日志函数（INFO/ERROR/DEBUG）和 `AsciiOutput` 调试输出
4. Data Tab 使用计数器追踪总行数、成功行数、`ItemReject` 跳过行数
5. 包含错误处理：`ProcessBreak`（Prolog）/ `ProcessQuit`（Epilog）

### 阶段 4：代码审查（ti-code-reviewer）

代码生成后，启动 ti-code-reviewer subagent 审查：

```
Agent(subagent_type="ti-code-reviewer", prompt="Review the TI Process code in processes/<process_name>/. Target cube dimension order: [Dim1, Dim2, ...].")
```

Reviewer 会以 `coding-conventions.md` 和 `ti-functions.md` 为标准审查四个 Tab、参数和变量。根据审查结果修正代码。

### 阶段 5：Human-in-the-loop 审查（由 spec_gate hook 强制执行）

本项目配置了 `spec_gate` hook，所有 MCP 写入工具需要 session 绑定和审查标记。

**流程：**
1. 展示代码文件 → 调用 `AskUserQuestion` 展示所有文件内容，询问是否正确
2. 用户确认后 → 创建 `.reviewed` 标记：`touch processes/<process_name>/.reviewed`
3. 进入部署阶段

未完成步骤 1-2 直接调用 `create_process` / `update_process` 会被 hook 拦截。代码文件被修改后（时间戳比 `.reviewed` 新）需重新审查。

### 阶段 6：部署到 TM1

使用 `create_process` 部署，将 7 个文件内容传入对应参数。如果 Process 已存在，用 `update_process` 只更新需要的字段。

部署完成后告知用户，询问是否需要执行测试。

### 阶段 7：测试

1. `compile_process` → 验证语法
2. `execute_process` → 执行测试
3. 检查返回结果，有错误用 `get_process_error_log` 查看详情
4. `execute_mdx` 或 `get_cell` → 验证目标 Cube 数据
5. 有错误用 `update_process` 修复后重新部署

## 参考资料使用

- **TI 函数不清楚** → `references/ti-functions.md`
- **MCP 工具用法不清楚** → `references/mcp-tools-reference.md`
- **设计阶段需要参考案例** → `references/ti-process-examples.md`
- **编码规范** → `references/coding-conventions.md`（每次生成代码前重新读取）

## 注意事项

- TI 脚本在服务器端执行，不要使用本地系统命令
- TI 函数名区分大小写，与 `ti-functions.md` 中的拼写一致
- CellPut 系列函数的维度顺序必须与 Cube 定义一致
- TM1py API 配置含敏感凭证，不要在代码注释或日志中输出
