# TM1 MCP 工具速查

> 供 Claude Code Agent 使用的 TM1 MCP 工具快速参考。

---

## 工具分类概览

| 类别 | 工具数 | 权限 |
|------|--------|------|
| 实例 | 1 | 只读 |
| Dimension | 5 | 只读 |
| Cube | 4 | 只读 |
| View | 2 | 只读 |
| Subset | 2 | 只读 |
| Cell | 2 | 只读 |
| Process 读取 | 5 | 只读 |
| Process 写入 | 2 | 写入 |
| Process 执行 | 1 | 执行（异步） |
| Process 删除 | 1 | 破坏性 |
| 工具 | 1 | 只读 |

---

## 一、实例工具

### list_instances()
列出所有配置的 TM1 实例名称。
- 返回: `list[str]` — 如 `["FDI", "OUFS_Dev"]`

---

## 二、Dimension 工具（只读）

渐进式探索：先 `get_dimension_info` 了解全貌 → 再 `get_leaf_elements` 看叶子 / `expand_element` 展开局部 / `get_parents` 查父级 / `get_element_attributes` 查属性值。

### list_dimensions(instance, filter=None, skip_control_dims=True)
列出所有 Dimension。可选按名称关键字过滤。
- `filter`: 名称关键字过滤（大小写不敏感）

### get_dimension_info(instance, dimension_name, hierarchy=None)
获取 Dimension 概览：元素类型分布（N/S/C 计数）、层级数、属性名列表、**根元素列表**。
**探索维度的第一步** — 一眼看到顶层结构。
- 返回: `{"dimension": ..., "element_counts": {"numeric": ..., "string": ..., "consolidated": ..., "total": ...}, "level_count": ..., "attribute_names": [...], "root_elements": [{"name": ..., "type": "C"}, ...]}`

### get_leaf_elements(instance, dimension_name, hierarchy=None, under=None, search=None, sample=None)
获取叶子（N/S）元素。
- `under`: 指定父级，返回该汇总节点下的全部叶子元素（**最常用场景**）
- `search`: 按名称关键字过滤（大小写不敏感）
- `sample`: 限制返回数量
- 返回: `{"dimension": ..., "under": "Total Revenue", "leaf_elements": [...], "total": ..., "truncated": bool}`

### expand_element(instance, dimension_name, element_name, hierarchy=None, depth=1, include_attributes=False)
展开指定元素查看子结构。渐进式深入：depth=1 只看直接子节点，不够再加深，depth=None 全量展开。
- `depth`: 展开深度（默认 1，None=不限制）
- `include_attributes`: 是否附带元素属性值
- 返回: `{"dimension": ..., "name": "Total Revenue", "type": "C", "children": [{"name": ..., "type": "N"}, ...]}`

### get_parents(instance, dimension_name, elements, hierarchy=None)
获取单个/批量元素的全部父级元素。 — 操作层级前必须知道元素归属。
- `elements`: 元素名称列表，支持批量查询
- 返回: `{"dimension": ..., "parents": {"elem1": ["parentA", "parentB"], "elem2": ["parentC"]}}`

### get_element_attributes(instance, dimension_name, hierarchy=None, elements=None, attribute_names=None)
获取元素属性值（非属性名列表）。**始终指定 `elements` 控制范围。**
- `elements`: 要查询的元素列表（强烈建议指定，避免全量拉取）
- `attribute_names`: 要查询的属性名列表（不指定则返回所有属性）
- 返回: `{"dimension": ..., "attributes": {"elem1": {"Description": "X", "中文名称": "Y"}, ...}}`

---

## 三、Cube 工具（只读）

### list_cubes(instance, filter=None, skip_control_cubes=True)
列出所有 Cube。可选按名称关键字过滤。

### get_cube(instance, cube_name)
获取 Cube 结构：维度顺序列表、最后数据更新时间、Rules 错误。

### find_cubes_by_dimension(instance, dimension_name, skip_control_cubes=True)
查找使用指定 Dimension 的所有 Cube。

### get_cube_rules(instance, cube_name)
获取 Cube 的完整 Rules 文本。无 Rules 时返回空字符串。

---

## 四、View 工具（只读）

### list_views(instance, cube_name)
列出 Cube 的所有 View（私有和公有分开）。
- 返回: `{"private": [...], "public": [...]}`

### get_view_structure(instance, cube_name, view_name, private=False)
获取 View 的完整结构：列/行/标题各轴的维度-Subset-元素分配详情。
- 返回: `{"columns": [{"dimension":..., "subset":..., "subset_type":..., "elements":[...]}], ...}`

---

## 五、Subset 工具（只读）

### list_subsets(instance, dimension_name, hierarchy=None, private=False)
列出 Dimension 的所有 Subset。

### get_subset(instance, dimension_name, subset_name, hierarchy=None)
获取 Subset 详情：元素列表、类型（static/dynamic）、动态 Subset 的 MDX 表达式。

---

## 六、Cell 工具（只读）

### get_cell(instance, cube_name, elements)
获取单个单元格的值。`elements` 必须按 Cube 维度顺序排列。

### execute_mdx(instance, mdx, top=None, skip_zeros=False, skip_consolidated=False, use_blob=False)
执行 MDX 查询，返回记录列表。支持原始 MDX 字符串或 MdxBuilder 对象。支持限制行数、跳过零值、跳过汇总。
- 示例：`execute_mdx(instance="FDI", mdx="SELECT ... FROM [General Ledger] ...", top=10, skip_zeros=True)`

### execute_view_query(instance, cube_name, view_name, private=False, top=None)
执行 Cube View，返回单元格数据记录列表。

---

## 七、Process 工具（读取）

### list_processes(instance, filter=None, skip_control_processes=True)
列出所有 TI Process。可选按名称关键字过滤。

### get_process(instance, process_name, include_code=True)
获取 Process 详情：参数、变量、数据源类型、四个 Tab 代码。
**⚠️ 上下文预算提示**：`include_code=True` 会返回完整 TI 代码（单个进程可达数千 token）。仅在需要参考编码模式时使用 `True`；只需了解参数签名或数据源类型时，使用 `include_code=False`。

### search_processes(instance, keyword, search_code=True)
按名称或代码内容搜索 Process。返回匹配列表及匹配类型。

### compile_process(instance, process_name)
编译 Process，返回语法错误列表。

### get_process_error_log(instance, process_name)
获取 Process 最近一次执行错误日志。

---

## 八、Process 工具（写入/执行/删除）

### create_process(instance, process_name, prolog="", metadata="", data="", epilog="", parameters=None, variables=None, datasource_type="None")
创建新的 TI Process。
- `parameters`: `[{"name":"pX","prompt":"...","value":"...","type":"String"},...]`
- `variables`: `[{"name":"vX","type":"String"},...]`

### update_process(instance, process_name, prolog=None, metadata=None, data=None, epilog=None, parameters=None, variables=None)
更新已有 TI Process。只传需要修改的字段，未传字段保持不变。

### execute_process(instance, process_name, parameters=None, timeout=None) — 异步
执行 TI Process。`parameters` 格式同 `create_process`。
- 返回: `{"success": bool, "status": str, "error_log": str, ...}`

### delete_process(instance, process_name) — 破坏性
永久删除 TI Process。

---

## 九、工具

### get_process_template()
返回空 Process 模板结构，供参考。

---

## 典型使用流程

### 场景 A：用户已提供精确对象名称（精确优先）

```
# 直接获取，不要先搜索
get_cube(instance="FDI", cube_name="General Ledger")
get_process(instance="FDI", process_name="Cub.GL.Data.Load.From.CSV", include_code=False)
  # ⚠️ 只需参数签名时用 include_code=False，节省 token
get_dimension_info(instance="FDI", dimension_name="Account")

# 按需深入 Dimension（仅在写入逻辑需要时）
get_leaf_elements(instance="FDI", dimension_name="Account", under="Total Revenue", sample=30)

# 信息充分即停 — 以下情况可以进入设计阶段：
# ✅ 已拿到 Cube 维度顺序 + 关键 Dimension 结构 + 被调用 Process 参数
# ❌ 不要继续搜索"类似进程"作为模板参考
```

### 场景 B：用户提供模糊描述，需要先发现再深入

```
# 1. 发现
list_instances()
list_cubes(instance="FDI", filter="GL")
search_processes(instance="FDI", keyword="GL")

# 2. 深入（渐进式探索 Dimension）
get_cube(instance="FDI", cube_name="General Ledger")
get_dimension_info(instance="FDI", dimension_name="Account")
→ 看到 roots: [Total Revenue, Total Expense, ...]，确定要操作的分支

expand_element(instance="FDI", dimension_name="Account", element_name="Total Revenue", depth=1)
→ 展开一层看子结构

get_leaf_elements(instance="FDI", dimension_name="Account", under="Total Revenue", search="Sales", sample=30)
→ 获取指定父级下的叶子元素

get_parents(instance="FDI", dimension_name="Account", elements=["Sales_A", "Sales_B"])
→ 批量查元素归属

get_element_attributes(instance="FDI", dimension_name="Account", elements=["Sales_A"])
→ 查属性的业务含义

# 3. 参考已有 Process（⚠️ 最多读 1-2 个，避免 token 浪费）
get_process(instance="FDI", process_name="Dim.Element.Update.COA", include_code=True)

# 4. 创建/部署 Process
create_process(
    instance="FDI",
    process_name="My.New.Process",
    prolog="...",
    metadata="...",
    data="...",
    epilog="...",
    parameters=[{"name":"pEntity","prompt":"Entity","value":"1000","type":"String"}],
)

# 5. 验证和测试
compile_process(instance="FDI", process_name="My.New.Process")
execute_process(instance="FDI", process_name="My.New.Process")
get_process_error_log(instance="FDI", process_name="My.New.Process")

# 6. 验证数据
execute_mdx(instance="FDI", mdx="SELECT ... FROM [General Ledger] WHERE ...", top=10, skip_zeros=True)

# 7. 清理
delete_process(instance="FDI", process_name="My.New.Process")
```