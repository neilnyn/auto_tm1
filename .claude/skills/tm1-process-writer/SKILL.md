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
需求文档/PRD → 连接TM1探索 → 设计Process → 生成7个文件 → 部署到TM1
                ↑                                    |
                └──── Human-in-the-loop 审查 ←────────┘
```

## 前置条件

在开始工作前，确认以下条件已满足：
1. 确认 `config/tm1py_config.ini` 文件存在且配置正确
2. 用户已提供开发需求文档（PRD 或功能说明）

### 从 tm1-model-builder 交接过来的场景

如果用户的消息中包含 "Model Build Summary for TI Development" 格式的交接文档，直接使用该文档中的信息作为需求输入：
- **Cubes Built** 部分提供了目标 Cube 名称和维度顺序 — 无需再次 `get_cube` 确认维度顺序
- **Subsets Created** 部分提供了可用的 Subset — 可直接用于数据源配置
- **Seed Data Written** 说明了已有数据 — 避免重复加载
- **What TI Should Automate** 即本 Process 的功能需求
- **TM1 Instance** 指明了目标实例 — 直接使用，无需 `list_instances`

在此场景下，可跳过部分环境探索步骤（如维度顺序确认），直接进入设计阶段。

## 详细工作步骤

### 阶段 1：需求分析 & TM1 环境探索

1. **获取需求**：向用户索要 PRD 或开发文档说明。如果用户尚未提供，主动询问：
   - 这个 TI Process 要完成什么功能？
   - 涉及哪些 Cube、Dimension 的读写？
   - 数据源是什么（ASCII 文件、TM1 Cube View、ODBC 等）？
   - 是否需要参数？有哪些参数？

2. **连接 TM1 并按需探索环境**（使用 MCP 工具，无需手动管理连接）：

   ### 何时使用 subagent

   - **精确查询（1-2 个 MCP 调用）**：直接调用 MCP 工具（如 `get_cube`、`get_process`）
   - **广泛探索（3+ 个连续 MCP 调用）**：委托给 `tm1-explorer` subagent（`Agent` tool with `subagent_type="tm1-explorer"`），避免主对话上下文爆炸
   - 典型场景：需要先列出多个 cube/dimension 再逐个深入、搜索多个 process 的代码模式、全面了解一个未知的 TM1 环境

   ### 使用 subagent注意事项
   - 注意事项：如果`tm1-explorer` subagent 返回了error message,please flag it,not ask `tm1-explorer` subagent to fix itself

   ### 探索效率原则（必读）

   **原则 1：精确优先** — 当用户或 PRD 已提供精确的对象名称（Cube 名、Process 名、Dimension 名）时，直接使用 `get_process` / `get_cube` / `get_dimension_info` 获取详情，**不要**先用 `list_*` 或 `search_*` 做模糊搜索再筛选。

   **原则 2：信息充分即停** — 每次调用 MCP 工具前先问自己"我还需要什么信息才能开始设计？"如果当前已获取的信息足以完成设计，立即停止探索，进入设计阶段。典型的充分条件：
   - 目标 Cube 的维度顺序（CellPutN / CellPutS 必须按此顺序）
   - 关键 Dimension 的元素结构（写入逻辑必须确认的过滤/映射元素）
   - 被调用 Process 的参数列表（ExecuteProcess 必须知道传哪些参数）
   - 数据源维度的过滤元素确认

   **原则 3：上下文预算意识** — `get_process(include_code=True)` 会返回完整 TI 代码，单个进程可消耗数千 token。读取前评估必要性：
   - 只需了解参数签名？→ 使用 `get_process(include_code=False)`
   - 需要参考编码模式？→ 只读 **1-2 个**参考进程，不要读 3 个以上
   - 已有编码规范文件？→ 优先参考 `.claude/skills/tm1-process-writer/references/` 下的文档，而非在线读取服务器上的进程代码
   - 被调用的 bedrock/工具进程？→ 只需读参数列表，不需要读完整代码

   ### 探索步骤

   **第一步：识别开发对象**
   ```
   根据用户指令或开发文档，识别需要操作的 TM1 对象。
   - 用户已提供精确名称 → 直接 get_cube / get_process / get_dimension_info
   - 用户提供模糊描述 → list_* + filter 搜索，再 get_* 深入
   ```

   **第二步：深入关键对象（渐进式探索）**
   ```
   → get_cube(instance="Neil", cube_name="<cube_name>")
     （返回维度顺序 — CellPutN 必须按此顺序！）
   → get_dimension_info(instance="Neil", dimension_name="<dim_name>")
     （一眼看到根元素和规模，确定要操作的分支）
   → get_leaf_elements(instance="Neil", dimension_name="<dim_name>", under="<parent>", sample=30)
     （获取指定父级下的叶子元素）
   → expand_element(instance="Neil", dimension_name="<dim_name>", element_name="<elem>", depth=1)
     （展开一层看子结构，不够再加深）
   → get_parents(instance="Neil", dimension_name="<dim_name>", elements=["<elem1>","<elem2>"])
     （查元素归属 — Metadata Tab 核心需求）
   → get_element_attributes(instance="Neil", dimension_name="<dim_name>", elements=["<elem>"])
     （查元素属性值）
   → get_process(instance="Neil", process_name="<existing_process>", include_code=True)
     （完整代码消耗大量 token，仅在需要参考编码模式时使用 include_code=True）
   ```

   **第三步（可选）：交叉引用**
   ```
   → find_cubes_by_dimension(instance="Neil", dimension_name="<dim_name>")
   → execute_mdx(instance="Neil", mdx="SELECT ... FROM <cube> ...", top=10)
   ```

   每次探索后将关键发现（Cube 维度顺序、Dimension 元素样本）整理展示给用户确认。

3. **Human-in-the-loop 检查点 #1**：将你对需求的理解和 TM1 环境分析结果展示给用户，询问以下问题：
   - 需求理解是否正确？
   - 涉及的数据对象是否完整？
   - 是否有遗漏的边界情况？

### 阶段 2：TI Process 设计（must-have）

根据需求和环境分析，设计 TI Process 的四个部分。在编码前，参考以下文件了解编码规范和最佳实践：
- `.claude/skills/tm1-process-writer/references/coding-conventions.md` — 必须遵循的编码规范
- `.claude/skills/tm1-process-writer/references/ti-functions.md` — 可用的 TI 函数速查

#### 四个 Tab 的设计原则：

**Prolog** — 执行前处理：
- 参数解析和验证
- 初始化变量、常量
- 检查前置条件（Cube 是否存在、数据是否已加载等）
- 使用 `ProcessBreak` 处理前置条件失败情况
- **数据源定义统一在 Prolog 末尾设置**（DataSourceType、DataSourceNameForServer 等），不在 datasource.json 中配置细节——datasource.json 仅记录数据源类型

**Metadata** — 元数据处理：
- 创建/更新 Dimension 结构（DimensionElementInsert、DimensionElementComponentAdd 等）
- 创建/更新 Subset（SubsetCreate、SubsetElementInsert 等）
- Dimension 维护逻辑

**Data** — 数据处理：
- 从数据源逐行读取并写入目标 Cube（CellPutN、CellPutS 等）
- 数据转换、校验逻辑
- 错误行使用 `ItemReject` 跳过
- 使用计数器变量追踪处理行数

**Epilog** — 执行后处理：
- 清理临时对象（View、Subset 销毁）
- 汇总日志输出（处理行数、错误行数）
- 使用 `AsciiOutput` 输出结果文件（如需要）
- 调用后续依赖的 Process（如有）

### 阶段 3：生成文件（must-have）

根据设计，在用户指定的目录下（默认为项目根目录 `processes/<process_name>/`），按 `.claude/skills/tm1-process-writer/templates/` 模板的格式，生成以下 7 个文件：

| 文件 | 说明 |
|------|------|
| `<process_name>_parameters.json` | TI 参数定义（参数名、类型、默认值、提示文本） |
| `<process_name>_datasource.json` | 数据源类型声明（仅记录类型：ASCII / TM1CubeView / SUBSET / ODBC，具体配置在 Prolog 代码中） |
| `<process_name>_variable.ti` | 变量定义（变量名、类型、位置等） |
| `<process_name>_prolog.ti` | Prolog 代码 |
| `<process_name>_metadata.ti` | Metadata 代码 |
| `<process_name>_data.ti` | Data 代码 |
| `<process_name>_epilog.ti` | Epilog 代码 |

#### 代码编写要求：

1. **遵循 `.claude/skills/tm1-process-writer/references/coding-conventions.md` 中定义的编码规范**
2. **每个 Tab 都要包含注释**，说明关键逻辑段的用途
3. **在合适位置使用日志函数**：
   - `LogOutput('INFO', ...)` — 关键步骤的信息日志
   - `LogOutput('ERROR', ...)` — 错误条件日志
   - `LogOutput('DEBUG', ...)` — 调试信息（变量值、中间状态）
   - `AsciiOutput('{ti_name}_data.debug',str1,str2,...str3)` — 调试信息（变量值、中间状态）
4. **在 Data Tab 中使用计数器**追踪：
   - 总处理行数
   - 成功写入行数
   - 被 `ItemReject` 跳过的行数
5. **在 Epilog Tab 中使用 `AsciiOutput` 输出处理结果摘要文件**（如需要）
6. **包含错误处理逻辑**：使用 `ProcessError` / `ProcessBreak` 处理不可恢复的错误

### 阶段 4：代码审查（ti-code-reviewer subagent）

代码生成后、提交用户审查前，启动 `ti-code-reviewer` subagent 对生成的代码进行审查：

```
Agent(subagent_type="ti-code-reviewer", prompt="Review the TI Process code in processes/<process_name>/. Target cube dimension order: [Dim1, Dim2, ...].")
```

Reviewer 会读取 `coding-conventions.md` 和 `ti-functions.md` 作为审查标准，检查四个 Tab、参数和变量是否合规。

根据审查结果修正代码，然后进入 Human-in-the-loop 检查点。

### 阶段 5：Human-in-the-loop 检查点（must-have）

将生成的 7 个文件内容（已通过 ti-code-reviewer 审查）展示给用户审查。用户可能会要求修改。修改完成后再次确认。

### 阶段 6：部署到 TM1 服务器

用户确认代码后，使用 MCP 工具 `create_process` 部署。将 7 个文件的内容按以下方式传入：

- `process_name`: 从目录名获取
- `prolog`: prolog.ti 的内容
- `metadata`: metadata.ti 的内容
- `data`: data.ti 的内容
- `epilog`: epilog.ti 的内容
- `parameters`: parameters.json 中定义的参数列表（格式：`[{"name":"pX","prompt":"...","value":"...","type":"String"},...]`）
- `variables`: variable.ti 中定义的变量列表（格式：`[{"name":"vX","type":"String"},...]`）
- `datasource_type`: datasource.json 中声明的类型

**关键设计原则**：数据源的具体配置（DataSourceType、DataSourceNameForServer、DatasourceCubeView、DatasourceASCIIHeaderRecords 等）已在 Prolog 代码中定义，MCP 工具只需要传入 Process 名称、四个 Tab 的代码文本、参数和变量，不需要逐项设置数据源属性。

如果 Process 已存在，使用 `update_process` 工具只更新需要的字段。

部署完成后，告知用户 Process 已创建，并询问是否需要执行测试。

### 阶段 7：测试

如果用户需要测试：
1. 使用 MCP 工具执行 Process：`compile_process(instance="Neil", process_name="name")` 先验证语法
2. 语法通过后执行：`execute_process(instance="Neil", process_name="name", parameters=[...])`
3. 检查返回的 `success`、`status` 字段，如有错误查看 `error_log`
4. 如需要详细错误日志：`get_process_error_log(instance="Neil", process_name="name")`
5. 验证目标 Cube 中的数据：`execute_mdx(instance="Neil", mdx="SELECT ...")` 或 `get_cell(...)`
6. 如发现错误，使用 `update_process` 修复代码后重新部署

## 参考资料使用说明

开发过程中，请读取以下参考文件（不要一次性全部加载）：

- **TI函数不清楚时** → 查`.claude/skills/tm1-process-writer/references/ti-functions.md`
- **MCP 工具用法不清楚时** → 查 `.claude/skills/tm1-process-writer/references/mcp-tools-reference.md`
- **设计阶段需要参考案例时** → 查 `.claude/skills/tm1-process-writer/references/ti-process-examples.md`

## 注意事项

- IBM TM1 TI 脚本在服务器端执行，不要使用任何本地系统命令
- TI 函数名区分大小写，务必与 `.claude/skills/tm1-process-writer/references/ti-functions.md` 中的拼写一致
- TM1py API 的配置信息包含敏感凭证，不要在任何代码注释或日志中输出
- CellPut 系列函数的目标 Cube 和维度顺序必须与 Cube 定义一致
- 每次生成代码时都重新读取 `.claude/skills/tm1-process-writer/references/coding-conventions.md` 以确保遵循最新规范
