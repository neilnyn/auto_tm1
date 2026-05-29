# TM1 TurboIntegrator 常用函数速查

本文档整理了 TM1 TI 开发中最常用的 50 个函数，按功能分类。

---

## 一、数据操作函数

### CellPutN
- **作用**: 向 Cube 单元格写入数值
- **语法**: `CellPutN(Value, Cube, e1, e2, ...en);`
- **参数**: Value-数值, Cube-Cube名, e1..en-维度元素(按Cube维度顺序)
- **示例**: `CellPutN(12345, 'SalesCube', 'Actual', 'North', 'Jan');`
- **注意**: 维度参数顺序必须与 Cube 定义一致

### CellPutS
- **作用**: 向 Cube 单元格写入字符串
- **语法**: `CellPutS(String, Cube, e1, e2, ...en);`
- **参数**: String-字符串, Cube-Cube名, e1..en-维度元素
- **示例**: `CellPutS('Approved', 'Budget', '2024', 'Q1');`
- **注意**: 维度参数顺序必须与 Cube 定义一致

### CellGetN
- **作用**: 从 Cube 单元格读取数值
- **语法**: `CellGetN(Cube, e1, e2, ...en);`
- **参数**: Cube-Cube名, e1..en-维度元素
- **返回**: 数值
- **示例**: `vValue = CellGetN('SalesCube', 'Actual', 'North', 'Jan');`
- **注意**: 维度参数顺序必须与 Cube 定义一致

### CellGetS
- **作用**: 从 Cube 单元格读取字符串
- **语法**: `CellGetS(Cube, e1, e2, ...en);`
- **参数**: Cube-Cube名, e1..en-维度元素
- **返回**: 字符串
- **示例**: `vStatus = CellGetS('Budget', '2024', 'Q1');`

### CellIncrementN
- **作用**: 增量更新 Cube 单元格数值(累加)
- **语法**: `CellIncrementN(Value, Cube, e1, e2, ...en);`
- **参数**: Value-增量值, Cube-Cube名, e1..en-维度元素
- **示例**: `CellIncrementN(100, 'SalesCube', 'Actual', 'North', 'Jan');`
- **注意**: 将指定值累加到现有单元格值

### CellIsUpdateable
- **作用**: 检查 Cube 单元格是否可写入
- **语法**: `CellIsUpdateable(Cube, e1, e2, ...en);`
- **返回**: 1-可写入, 0-不可写入
- **示例**: `IF(CellIsUpdateable('SalesCube', 'Actual', 'North') = 1, ...);`

---

## 二、维度操作函数

### DimensionCreate
- **作用**: 创建新维度
- **语法**: `DimensionCreate(DimName);`
- **参数**: DimName-维度名称
- **示例**: `DimensionCreate('Product');`

### DimensionDestroy
- **作用**: 删除维度
- **语法**: `DimensionDestroy(DimName);`
- **参数**: DimName-要删除的维度名称
- **示例**: `DimensionDestroy('Product');`
- **注意**: 删除维度会删除相关 Cube 数据

### DimensionExists
- **作用**: 检查维度是否存在
- **语法**: `DimensionExists(DimName);`
- **返回**: 1-存在, 0-不存在
- **示例**: `IF(DimensionExists('Product') = 0, DimensionCreate('Product'), '');`

### DimensionElementInsert
- **作用**: 向维度添加元素
- **语法**: `DimensionElementInsert(DimName, InsertionPoint, ElName, ElType);`
- **参数**: 
  - DimName-维度名
  - InsertionPoint-插入位置(空字符串表示末尾)
  - ElName-元素名
  - ElType-元素类型: N(数值), S(字符串), C(合并)
- **示例**: `DimensionElementInsert('Region', 'Belgium', 'Netherlands', 'N');`
- **注意**: 只能在 Prolog 或 Metadata 过程中使用

### DimensionElementInsertDirect
- **作用**: 直接向维度添加元素(不创建编辑副本)
- **语法**: `DimensionElementInsertDirect(DimName, InsertionPoint, ElName, ElType);`
- **参数**: 同 DimensionElementInsert
- **示例**: `DimensionElementInsertDirect('Region', '', 'NewElement', 'N');`
- **注意**: 适用于大数据量加载,可在 Data 过程中使用

### DimensionElementDelete
- **作用**: 从维度删除元素
- **语法**: `DimensionElementDelete(DimName, ElName);`
- **参数**: DimName-维度名, ElName-要删除的元素名
- **示例**: `DimensionElementDelete('Region', 'Belgium');`
- **注意**: 删除元素会删除相关 Cube 数据

### DimensionElementComponentAdd
- **作用**: 向合并元素添加子元素
- **语法**: `DimensionElementComponentAdd(DimName, ConsolidatedElName, ElName, ElWeight);`
- **参数**: 
  - DimName-维度名
  - ConsolidatedElName-父元素(合并元素)
  - ElName-子元素名
  - ElWeight-权重(正数相加,负数相减)
- **示例**: `DimensionElementComponentAdd('Measures', 'Net Sales', 'Expenses', -1);`
- **注意**: 不能在 Epilog 过程中使用

### DimensionDeleteAllElements
- **作用**: 删除维度中所有元素
- **语法**: `DimensionDeleteAllElements(DimName);`
- **参数**: DimName-维度名
- **示例**: `DimensionDeleteAllElements('Model');`
- **注意**: 用于重建维度层级,数据可保留

### DimensionSortOrder
- **作用**: 设置维度排序方式
- **语法**: `DimensionSortOrder(DimName, CompSortType, CompSortSense, ElSortType, ElSortSense);`
- **参数**: 
  - CompSortType: ByInput/ByName
  - CompSortSense: Ascending/Descending
  - ElSortType: ByInput/ByName/ByLevel/ByHierarchy
  - ElSortSense: Ascending/Descending
- **示例**: `DimensionSortOrder('Region', 'ByName', 'Descending', 'ByLevel', 'Ascending');`

### DimensionElementPrincipalName
- **作用**: 获取元素的主名称(非别名)
- **语法**: `DimensionElementPrincipalName(DimName, ElName);`
- **返回**: 元素的主名称
- **示例**: `vPrincipalName = DimensionElementPrincipalName('Product', 'ProductAlias');`

---

## 三、属性操作函数

### AttrInsert
- **作用**: 为维度创建新属性
- **语法**: `AttrInsert(DimName, PrevAttr, AttrName, Type);`
- **参数**: 
  - DimName-维度名
  - PrevAttr-前一个属性名(空表示第一个)
  - AttrName-新属性名
  - Type: N(数值), S(字符串), A(别名)
- **示例**: `AttrInsert('Model', 'Transmission', 'InteriorColor', 'S');`

### AttrDelete
- **作用**: 删除维度属性
- **语法**: `AttrDelete(DimName, AttrName);`
- **参数**: DimName-维度名, AttrName-属性名
- **示例**: `AttrDelete('Model', 'InteriorColor');`

### AttrPutN
- **作用**: 设置元素的数值属性值
- **语法**: `AttrPutN(Value, DimName, ElName, AttrName, [LangLocaleCode]);`
- **参数**: Value-数值, DimName-维度名, ElName-元素名, AttrName-属性名
- **示例**: `AttrPutN(2257993, 'Model', 'S Series', 'ProdCode');`

### AttrPutS
- **作用**: 设置元素的字符串属性值
- **语法**: `AttrPutS(Value, DimName, ElName, AttrName, [LangLocaleCode]);`
- **参数**: Value-字符串, DimName-维度名, ElName-元素名, AttrName-属性名
- **示例**: `AttrPutS('Beige', 'Model', 'S Series', 'InteriorColor');`

### ATTRNL
- **作用**: 获取元素的数值属性值
- **语法**: `ATTRNL(DimName, ElName, AttrName, [LangLocaleCode]);`
- **返回**: 数值属性值
- **示例**: `vValue = ATTRNL('Model', 'L Series', 'Engine Size', 'fr');`
- **注意**: [LangLocaleCode]为可选参数,可不用传参
### ATTRSL
- **作用**: 获取元素的字符串属性值
- **语法**: `ATTRSL(DimName, ElName, AttrName, [LangLocaleCode]);`
- **返回**: 字符串属性值
- **示例**: `vCurrency = ATTRSL('Plan_Business_Unit', '10100', 'Currency', 'fr');`
- **注意**: [LangLocaleCode]为可选参数,可不用传参
---

## 四、Cube 操作函数

### CubeCreate
- **作用**: 创建新 Cube
- **语法**: `CubeCreate(Cube, d1, d2, ...dn);`
- **参数**: Cube-Cube名, d1..dn-维度名(按顺序)
- **示例**: `CubeCreate('SalesCube', 'Scenario', 'Region', 'Product', 'Month');`
- **注意**: 维度顺序决定 Cube 结构

### CubeExists
- **作用**: 检查 Cube 是否存在
- **语法**: `CubeExists(CubeName);`
- **返回**: 1-存在, 0-不存在
- **示例**: `IF(CubeExists('SalesCube') = 0, CubeCreate('SalesCube', ...), '');`

### CubeClearData
- **作用**: 清空 Cube 中所有数据
- **语法**: `CubeClearData(CubeName);`
- **参数**: CubeName-Cube名
- **示例**: `CubeClearData('SalesCube');`
- **注意**: 清空后数据无法恢复

### CubeUnload
- **作用**: 从内存卸载 Cube
- **语法**: `CubeUnload(CubeName);`
- **参数**: CubeName-Cube名
- **示例**: `CubeUnload('ManufacturingBudget');`
- **注意**: 卸载后首次访问会重新加载

### CubeSetLogChanges
- **作用**: 设置 Cube 的日志属性
- **语法**: `CubeSetLogChanges(Cube, LogChanges);`
- **参数**: Cube-Cube名, LogChanges-1开启/0关闭
- **示例**: `CubeSetLogChanges('SalesCube', 1);`

### CubeSaveData
- **作用**: 将 Cube 数据序列化到磁盘
- **语法**: `CubeSaveData(Cube);`
- **参数**: Cube-Cube名
- **示例**: `CubeSaveData('SalesCube');`
- **注意**: 用于数据加载后保存,提高安全性

---

## 五、Subset 操作函数

### SubsetCreate
- **作用**: 创建空 Subset
- **语法**: `SubsetCreate(DimName, SubName, <AsTemporary>);`
- **参数**: 
  - DimName-维度名
  - SubName-Subset名
  - AsTemporary-可选,1临时/0永久
- **示例**: `SubsetCreate('Region', 'Northern Europe', 1);`

### SubsetCreateByMDX
- **作用**: 使用 MDX 创建 Subset
- **语法**: `SubsetCreatebyMDX(SubName, MDX_Expression, <AsTemporary>);`
- **参数**: SubName-Subset名, MDX_Expression-MDX表达式
- **示例**: `SubsetCreatebyMDX('0-level months', '{TM1FILTERBYLEVEL({TM1SUBSETALL([month])}, 0)}', 1);`

### SubsetDestroy
- **作用**: 删除 Subset
- **语法**: `SubsetDestroy(DimName, SubName);`
- **参数**: DimName-维度名, SubName-Subset名
- **示例**: `SubsetDestroy('Region', 'Northern Europe');`

### SubsetElementInsert
- **作用**: 向 Subset 添加元素
- **语法**: `SubsetElementInsert(DimName, SubName, ElName, Position);`
- **参数**: DimName-维度名, SubName-Subset名, ElName-元素名, Position-位置
- **示例**: `SubsetElementInsert('Region', 'Northern Europe', 'Finland', 3);`

### SubsetElementDelete
- **作用**: 从 Subset 删除元素
- **语法**: `SubsetElementDelete(DimName, SubName, Index);`
- **参数**: DimName-维度名, SubName-Subset名, Index-元素索引
- **示例**: `SubsetElementDelete('Region', 'Northern Europe', 3);`

### SubsetDeleteAllElements
- **作用**: 删除 Subset 中所有元素
- **语法**: `SubsetDeleteAllElements(DimName, SubsetName);`
- **参数**: DimName-维度名, SubsetName-Subset名
- **示例**: `SubsetDeleteAllElements('Region', 'Central Europe');`

### SubsetExists
- **作用**: 检查 Subset 是否存在
- **语法**: `SubsetExists(DimName, SubsetName);`
- **返回**: 1-存在, 0-不存在
- **示例**: `IF(SubsetExists('Region', 'Europe') = 0, SubsetCreate('Region', 'Europe'), '');`

### SubsetGetSize
- **作用**: 获取 Subset 元素数量
- **语法**: `SubsetGetSize(DimName, SubsetName);`
- **返回**: 元素数量
- **示例**: `vCount = SubsetGetSize('Region', 'EurAsia');`

---

## 六、View 操作函数

### ViewCreate
- **作用**: 创建 Cube 视图
- **语法**: `ViewCreate(Cube, ViewName, <AsTemporary>);`
- **参数**: Cube-Cube名, ViewName-视图名, AsTemporary-可选
- **示例**: `ViewCreate('Sales', '1st Quarter Actuals', 1);`

### ViewDestroy
- **作用**: 删除 Cube 视图
- **语法**: `ViewDestroy(Cube, ViewName);`
- **参数**: Cube-Cube名, ViewName-视图名
- **示例**: `ViewDestroy('Sales', '1st Quarter Actuals');`

### ViewCreateByMDX
- **作用**: 使用 MDX 创建视图
- **语法**: `ViewCreateByMDX(Cube, ViewName, MDX_expression, <AsTemporary>);`
- **参数**: Cube-Cube名, ViewName-视图名, MDX_expression-MDX表达式
- **示例**: `ViewCreateByMDX('Sales', 'Account', 'SELECT ...');`

---

## 七、进程控制函数

### ExecuteProcess
- **作用**: 执行另一个 TI 进程
- **语法**: `ExecuteProcess(ProcessName, [ParamName1, ParamValue1, ...]);`
- **参数**: ProcessName-进程名, ParamName/ParamValue-参数名值对
- **返回**: 进程执行状态码
- **示例**: `ExecuteProcess('create_sales_cube', 'pYear', '2024');`
- **注意**: 可用返回值判断执行结果

### ProcessBreak
- **作用**: 停止处理数据源,跳转到 Epilog
- **语法**: `ProcessBreak;`
- **示例**: `IF(vError = 1, ProcessBreak);`

### ProcessError
- **作用**: 立即终止进程(错误状态)
- **语法**: `ProcessError;`
- **示例**: `IF(vFatalError = 1, ProcessError);`
- **注意**: 进程标记为错误状态

### ProcessQuit
- **作用**: 终止 TI 进程
- **语法**: `ProcessQuit;`
- **示例**: `ProcessQuit;`

### ProcessExists
- **作用**: 检查进程是否存在
- **语法**: `ProcessExists(ProcessName);`
- **返回**: 1-存在且有效, 0-不存在, -1-存在但有编译错误
- **示例**: `IF(ProcessExists('my_process') = 1, ExecuteProcess('my_process'));`

### ItemReject
- **作用**: 拒绝当前数据源记录并写入错误日志
- **语法**: `ItemReject(ErrorString);`
- **参数**: ErrorString-错误信息
- **示例**: `ItemReject('Value outside of acceptable range.');`
- **注意**: 只在 Data 过程中有效

### ItemSkip
- **作用**: 跳过当前数据源记录
- **语法**: `ItemSkip;`
- **示例**: `IF(vValue = 0, ItemSkip);`
- **注意**: 只在 Data 过程中有效

---

## 八、文件操作函数

### ASCIIOutput
- **作用**: 向 ASCII 文件写入逗号分隔记录
- **语法**: `ASCIIOutput(FileName, String1, String2, ...Stringn);`
- **参数**: FileName-文件路径, String1..n-字段值
- **示例**: `ASCIIOutput('C:\temp\output.csv', V1, V2, V3);`
- **注意**: 每条记录最大 8000 字节

### ASCIIDelete
- **作用**: 删除 ASCII 文件
- **语法**: `ASCIIDelete(FileName);`
- **参数**: FileName-文件路径
- **示例**: `ASCIIDelete('C:\temp\output.csv');`

### TextOutput
- **作用**: 向文本文件写入逗号分隔记录
- **语法**: `TextOutput(FileName, String1, String2, ...Stringn);`
- **参数**: FileName-文件路径, String1..n-字段值
- **示例**: `TextOutput('C:\temp\output.txt', V1, V2, V3);`
- **注意**: 可用 SetOutputCharacterSet 设置字符编码

### SetInputCharacterSet
- **作用**: 设置数据源字符编码
- **语法**: `SetInputCharacterSet(CharacterSet);`
- **参数**: CharacterSet-编码类型(如 TM1CS_UTF8)
- **示例**: `SetInputCharacterSet('TM1CS_UTF8');`

### SetOutputCharacterSet
- **作用**: 设置输出文件字符编码
- **语法**: `SetOutputCharacterSet(FileName, CharacterSet);`
- **参数**: FileName-文件路径, CharacterSet-编码类型
- **示例**: `SetOutputCharacterSet('output.txt', 'TM1CS_UTF8');`

---


## 九、数据类型转换函数

### NumberToString
- **作用**: 数字转字符串(使用当前区域设置)
- **语法**: `NumberToString(Value);`
- **参数**: Value-数值
- **返回**: 字符串
- **示例**: `sRet = NumberToString(1234.5);`

### NumberToStringEx
- **作用**: 数字转字符串(自定义格式)
- **语法**: `NumberToStringEx(Value, NumericFormat, DecimalSep, ThousandsSep);`
- **参数**: Value-数值, NumericFormat-格式, DecimalSep-小数分隔符, ThousandsSep-千位分隔符
- **示例**: `sRet = NumberToStringEx(7895.23, '#,0.#########', ',', '.');`

### StringToNumber
- **作用**: 字符串转数字(使用当前区域设置)
- **语法**: `StringToNumber(String);`
- **参数**: String-字符串
- **返回**: 数值
- **示例**: `nRet = StringToNumber('123.45');`

### StringToNumberEx
- **作用**: 字符串转数字(自定义分隔符)
- **语法**: `StringToNumberEx(String, DecimalSep, ThousandsSep);`
- **参数**: String-字符串, DecimalSep-小数分隔符, ThousandsSep-千位分隔符
- **示例**: `nRet = StringToNumberEx('12,453.45', '.', ',');`

---

## 十、其他常用函数

### If 语句
- **作用**: 条件判断语句
- **语法**: 
  ```
  If(expression);
      statement1;
  ElseIf(expression);
      statement2;
  Else;
      statement3;
  EndIf;
  ```
- **示例**: 
  ```
  If(vValue > 100);
      CellPutN(vValue, 'Cube', 'A');
  Else;
      CellPutN(0, 'Cube', 'A');
  EndIf;
  ```
- **注意**: 最多嵌套 20 层

### TM1User
- **作用**: 获取当前 TM1 用户名
- **语法**: `TM1User()`
- **返回**: 用户名字符串
- **示例**: `sUser = TM1User();`

### GetProcessName
- **作用**: 获取当前进程名
- **语法**: `GetProcessName()`
- **返回**: 进程名字符串
- **示例**: `sName = GetProcessName();`

### GetProcessErrorFilename
- **作用**: 获取进程错误日志文件名
- **语法**: `GetProcessErrorFilename;`
- **返回**: 错误日志文件名(无错误返回空字符串)
- **示例**: `sErrorFile = GetProcessErrorFilename;`

### WildcardFileSearch
- **作用**: 使用通配符搜索文件
- **语法**: `WildcardFileSearch(Pathname, PriorFilename);`
- **参数**: 
  - Pathname-路径和通配符文件名
  - PriorFilename-上一个文件名(空字符串表示从头开始)
- **返回**: 匹配的文件名
- **示例**: `file = WildcardFileSearch('C:\temp\*.csv', '');`

### HierarchyCreate
- **作用**: 创建新层级
- **语法**: `HierarchyCreate(DimName, HierName);`
- **参数**: DimName-维度名, HierName-层级名
- **示例**: `HierarchyCreate('Vehicles', 'Trucks');`

### HierarchyElementInsert
- **作用**: 向层级添加元素
- **语法**: `HierarchyElementInsert(DimName, HierName, InsertionPoint, ElName, ElType);`
- **参数**: DimName-维度名, HierName-层级名, InsertionPoint-插入位置, ElName-元素名, ElType-类型
- **示例**: `HierarchyElementInsert('Region', 'Western', 'Belgium', 'Netherlands', 'N');`

### ODBCOpen
- **作用**: 打开 ODBC 数据源连接
- **语法**: `ODBCOpen(Source, ClientName, Password);`
- **参数**: Source-数据源名, ClientName-用户名, Password-密码
- **示例**: `ODBCOpen('Accounting', 'Jdoe', 'Bstone');`

### ODBCOutput
- **作用**: 执行 SQL 语句
- **语法**: `ODBCOutput(Source, SQLQuery, [SQLQuery2, ...]);`
- **参数**: Source-数据源名, SQLQuery-SQL语句
- **示例**: `ODBCOutput('Accounting', 'INSERT INTO Categories VALUES(...)');`

---

## 进程执行返回值

ExecuteProcess 返回值可用以下函数判断:

| 函数 | 说明 |
|------|------|
| `ProcessExitNormal()` | 正常执行完成 |
| `ProcessExitMinorError()` | 执行成功但有轻微错误 |
| `ProcessExitSeriousError()` | 因严重错误退出 |
| `ProcessExitByQuit()` | 因 Quit 命令退出 |
| `ProcessExitByBreak()` | 因 ProcessBreak 退出 |
| `ProcessExitByChoreQuit()` | 因 ChoreQuit 退出 |
| `ProcessExitWithMessage()` | 正常退出并写入消息到日志 |
| `ProcessExitOnInit()` | 初始化时中止 |

---

## 元素类型说明

| 类型代码 | 说明 |
|---------|------|
| N | 数值元素 (Numeric) |
| S | 字符串元素 (String) |
| C | 合并元素 (Consolidated) |

---

## 属性类型说明

| 类型代码 | 说明 |
|---------|------|
| N | 数值属性 |
| S | 字符串属性 |
| A | 别名属性 (Alias) |


### Expand
- **作用**: 用于在运行时将 TurboIntegrator 中被 % 符号包围的变量名展开/替换为其实际值
- **语法**: Expand(String);
- **参数**: 字符串变量
- **示例**: 
	```
	V1 = 'SalesCube';
	ODBCOutput(datasource, Expand("INSERT INTO table VALUES ('%V1%')"));
	```
