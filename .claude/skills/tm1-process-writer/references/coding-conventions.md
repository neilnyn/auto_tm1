# TI Process 编码规范

本文档从真实 TI Process 案例中提取编码规范和约定，所有代码生成必须遵循这些规范。

---

## 一、Process 命名规范

Process 名称使用点号(`.`)分隔的多段命名：

**格式**: `{Type}.{Description}.From.{Source}`

| Type | 适用场景 |
|------|---------|
| `Dim` | 维度操作（Element 增删、属性维护） |
| `Cub` | Cube 数据操作（数据加载、数据迁移） |

**示例**:
- `Dim.Element.Update.COA Dimensions.From Master Data.CSV` — 维度更新，数据源为 CSV
- `Cub.Management Report PnL By YearMonth Natural.From.D8 Profit Loss` — Cube 数据加载，数据源为另一个 Cube

---

## 二、变量命名规范

### 2.1 前缀规则

| 前缀 | 含义 | 用途 | 示例 |
|------|------|------|------|
| `c` | Constant | 常量（Cube名、Dimension名、固定元素名等） | `cDim`, `cCubeTarget`, `cAttr01`, `cDelimDim` |
| `s` | String | 字符串变量（临时字符串、拼接结果、日志） | `sErr`, `sFilter`, `sProc`, `sTimeStamp` |
| `n` | Numeric | 数值变量（计数器、时间戳、错误计数） | `nErr`, `nDataRecordCount`, `nProcessStartTime` |
| `v` | Variable | 数据源变量（从数据源读入的字段值） | `vDimCode`, `vValue`, `vYear`, `vMonth` |
| `p` | Parameter | TI Process 参数 | `pScenario`, `pVersion`, `pYear`, `pMonth`, `pFile` |

### 2.2 命名风格

- 使用 **CamelCase**（驼峰命名），首字母小写，后续单词首字母大写
- 常量名应具有描述性，如 `cCubeSource` 而不是 `cSrc`
- 多个同类对象使用数字后缀区分：`cAttr01`, `cAttr02` / `cConsol01`, `cConsol02`
- 数据源变量建议使用有意义的名称：`vCodeChild`, `vNameChild` 而非 `V1`, `V2`

### 2.3 变量声明对齐

常量声明使用 Tab 对齐提高可读性：
```ti
cCubParam =     '}APQ Settings';
cDim =          'Account GL';
sTimeStamp =    TimSt( Now, '\Y\m\d\h\i\s' );
nErr =          0;
sErr =          '';
```

---

## 三、代码文件结构

### 3.1 Prolog 文件结构（从上到下）

```
1. PURPOSE 注释块（1-3 行描述 Process 功能）
2. DATA SOURCE 说明
3. INTENDED USAGE 说明
4. CHANGE HISTORY 表格（日期/修改人/说明）
5. ### Logging — APQ 框架日志初始化（如适用）
6. ### Params — 参数日志记录
7. ### Inits — 常量声明
8. 错误变量初始化（nErr = 0; sErr = '';）
9. 分隔符常量（如使用 Cube View 数据源）
10. 参数校验（使用 ProcessBreak）
11. 前置条件检查（Cube/Dim/File 是否存在）
12. 数据源配置（放在 Prolog 末尾）
```

### 3.2 Metadata 文件结构

```
1. 目标维度处理逻辑
2. Element 插入（先检查是否存在再插入）
3. Hierarchy 父子关系构建
4. 多个维度按顺序排列
```

### 3.3 Data 文件结构

```
1. ### Data script 标题
2. ### Mapping — 映射逻辑（查找目标元素）
3. 数据转换逻辑
4. Cell 写入操作（CellPutN / CellPutS / CellIncrementN）
5. 属性写入操作（如有）
```

### 3.4 Epilog 文件结构

```
1. ### Epilog script 标题
2. 恢复被修改的设置（如 Cube Logging）
3. 清理临时对象（View、Subset）
4. 调用后续依赖 Process
5. 错误检查（IF(nErr <> 0); ProcessQuit(); ENDIF;）
6. ### Logging — APQ 框架日志收尾
```

### 3.5 数据源配置模式（统一在 Prolog 末尾设置）

数据源的详细配置始终在 Prolog 代码末尾完成，不在 `datasource.json` 中配置细节，也不通过 TM1py API 设置。`datasource.json` 仅声明 `datasource_type`。部署时 TM1py API 只需传入 Process 名称和四个 Tab 的代码文本。

#### 模式一：CSV 文件数据源

```ti
DataSourceType = 'CHARACTERDELIMITED';
DatasourceNameForServer = sSourceFullPath;
# 如果 csv 有 header
DatasourceASCIIHeaderRecords = 1;
DatasourceASCIIDelimiter = ',';
DatasourceASCIIDecimalSeparator = '.';
DatasourceASCIIThousandSeparator = '';
```

`sSourceFullPath` 通常来自系统配置 Cube 或参数拼接：
```ti
cFilePath = CellGetS(cCubSysParam, 'TM1 Source Data Directory', 'Text');
sSourceFullPath = cFilePath | 'data_file.csv';
```

#### 模式二：Cube View 数据源

View 创建逻辑写在 Prolog 中（创建临时 View、设置过滤器、指定 View 提取参数），数据源声明放在 Prolog 末尾：
```ti
DataSourceType = 'VIEW';
DatasourceNameForServer = cCubeSource;
DatasourceCubeView = cView;
```

#### 模式三：Dimension Subset 数据源

```ti
DataSourceType = 'SUBSET';
DataSourceNameForServer = sDimName;
DatasourceDimensionSubset = sSubName;
```

---

## 四、注释规范

### 4.1 注释符号

| 符号 | 用途 |
|------|------|
| `#` | 单行注释、逻辑说明 |
| `###` | 区块标题（Section Header） |
| `####################` | 重大区块分隔线 |

### 4.2 Prolog 顶部注释模板

```ti
### PURPOSE:
### A 1 - 3 line description of what this process does goes here!
### 
### DATA SOURCE: <file name or cube name>
### 
### INTENDED USAGE: <when and how this process should be used>
### 
########################################################################################
### CHANGE HISTORY:
### MODIFICATION DATE 	CHANGED BY 	COMMENT
### YYYY-MM-DD 		Developer Name 	Reason for modification here
### 
########################################################################################
```

### 4.3 代码内注释

- 每个逻辑区块前用简短注释说明用途
- 使用 `#` 开头的单行注释，不强制中英文
- 关键判断条件应注释说明意图
- E.g. 模式：在注释后跟示例写法供参考

```ti
# Check File Existence
cFileName = pFile;
IF(FileExists(cFileName) = 0);
  nErr = nErr + 1;
  sErr = 'Data source file: ' | cFileName | ' doesnt exist';
  ProcessBreak;
ENDIF;

# E.g.1 sProcLogParams = Expand( 'pParam1:%pParam1% & pParam2:%pParam2%' );
# E.g.2 sProcLogParams = 'pParam1:' | pParam1 |' & '| 'pParam2:' | pParam2;
```

---

## 五、错误处理规范

### 5.1 错误变量约定

每个 Process 必须声明以下错误变量：
```ti
nErr = 0;      # 错误计数器
sErr = '';     # 错误信息字符串
```


### 5.2 Prolog 参数校验模式

对每个参数逐一校验是否在对应 Dimension 中存在：
```ti
### Test parameters
# pScenario
sDim = 'Scenario';
IF ( pScenario @<> '' & DimIx ( sDim , pScenario ) = 0 );
  nError = nError + 1;
  sErrorString = 'Element "' | pScenario | '" not found in dimension "' | sDim | '", Please check your data source.';
  ProcessBreak;
ENDIF;
```

### 5.3 文件存在性检查

```ti
cFileName = pFile;
IF(FileExists(cFileName) = 0);
  nErr = nErr + 1;
  sErr = 'Data source file: ' | cFileName | ' doesnt exist';
  ProcessBreak;
ENDIF;
```

### 5.4 维度和 Cube 存在性检查

```ti
IF(DimensionExists(cDim) = 0);
    DimensionCreate(cDim);
ENDIF;

IF(CubeExists(cCubeName) = 0);
    # handle missing cube
ENDIF;
```

### 5.5 Epilog 最终错误检查

```ti
### Err Handling
If (nErr <> 0);
  LogOutput('ERROR', sErr);
  ProcessQuit();
Endif;
```

### 5.6 ProcessBreak vs ProcessQuit vs ProcessError

| 函数 | 使用场景 | 使用位置 |
|------|---------|---------|
| `ProcessBreak` | 检测到无法继续的条件，立即停止后续所有处理 | Prolog（参数校验、文件检查） |
| `ProcessQuit()` | 在所有处理完成后根据累计错误决定是否标记失败 | Epilog（最终错误检查） |
| `ProcessError` | 一般性错误抛出不常用，通常用以上两种 | 按需使用 |

---

## 六、日志规范

### 6.1 APQ Cubewise APLIQODE 日志框架（标准格式）

建议使用 Cubewise APLIQODE 框架 (如果存在}APQ Process Execution Log这个cube对象)，在 Prolog 开头和 Epilog 末尾必须嵌入标准日志代码块。ti参数设置pDoProcessLogging = 1,参考 `ti-process-examples.md` 中示例2的完整代码块。

**Prolog 日志初始化**（放在 Prolog 开头，CHANGE HISTORY 之后）:
```ti
### Logging - common script 	-----------------  START (CUBEWISE APLIQODE FRAMEWORK)
sThisProcName = GetProcessName();
### Params
sProcLogParams = '';
sProcLogParams = sProcLogParams | 'pScenario: ' | pScenario;
# ... log all parameters
IF( pDoProcessLogging @= '1' );
  IF( sProcLogParams @<> '' );
    LogOutput( 'INFO', sThisProcName | ' run with parameters ' | sProcLogParams );
  EndIF;
  cCubTgt = '';
  sProcLogCube = '}APQ Process Execution Log';
  sCubLogCube = '}APQ Cube Last Updated by Process';
  nProcessStartTime = Now();
  nProcessFinishTime = 0;
  nMetaDataRecordCount = 0;
  nDataRecordCount = 0;
  NumericGlobalVariable( 'PrologMinorErrorCount' );  PrologMinorErrorCount = 0;
  NumericGlobalVariable( 'MetadataMinorErrorCount' );  MetadataMinorErrorCount = 0;
  NumericGlobalVariable( 'DataMinorErrorCount' );  DataMinorErrorCount = 0;
  NumericGlobalVariable( 'ProcessReturnCode' );  ProcessReturnCode = 0;
  sProcessErrorLogFile = '';
  sProcessRunBy = TM1User();
  # ... time tracking and CellPutN logging to }APQ Process Execution Log ...
EndIF;
### Logging - common script 	-----------------  END
```

**Epilog 日志收尾**（放在 Epilog 末尾，最后执行的代码块）:
```ti
### Logging - common script 	----------------- START (CUBEWISE APLIQODE FRAMEWORK)
### ( Place as last code block on epilog )
IF( pDoProcessLogging @= '1' );
  nProcessFinishTime = Now();
  # ... CellPutN for finish time, record counts, return code, error log file ...
  IF( nDataRecordCount > 0 );
    IF( cCubTgt @<> '' );
      CellPutN( nProcessFinishTime, sCubLogCube, cCubTgt, 'nLastTimeUpdate' );
    EndIF;
  EndIF;
EndIF;
```

> 注意：完整的长代码块请直接参照 `ti-process-examples.md`，生成代码时保持与示例一致。

### 6.2 简化日志（适用于简单 Process）

非 APQ 框架环境时，使用以下简化日志模式：

```ti
# Process 开始时
sThisProcName = GetProcessName();
sProcLogParams = 'pFile: ' | pFile;
LogOutput('INFO', sThisProcName | ' started with params: ' | sProcLogParams);

# 数据处理进度
LogOutput('INFO', 'Processed ' | NumberToString(nProcessedRows) | ' rows...');

# 错误
LogOutput('ERROR', 'Data source file not found: ' | cFileName);

# Process 结束时
LogOutput('INFO', sThisProcName | ' completed. Rows: ' | NumberToString(nProcessedRows));
```

### 6.3 LogOutput 级别约定

| 级别 | 用途 |
|------|------|
| `'INFO'` | Process 开始/结束、关键步骤完成、处理进度 |
| `'ERROR'` | 文件不存在、参数非法、维度/Cube 缺失等前置条件失败 |
| `'DEBUG'` | 变量值输出、中间状态检查（临时使用，上线前应移除） |
| `'WARN'` | 可恢复的异常情况 |

### 6.4 AsciiOutput 调试输出

在 Data Tab 中输出调试信息到文件：
```ti
AsciiOutput('{ti_name}_data.debug', vField1, vField2, vField3);
```

---

## 七、Cube View 数据源操作规范

### 7.1 分隔符常量

使用特殊字符作为 Filter 分隔符，避免与元素名冲突：
```ti
cDelimDim = Char(176);        # 维度分隔符 (°)
cDelimElemStart = Char(177);  # 元素开始分隔符 (±)
cDelimElement = Char(178);    # 元素内部多值分隔符 (²)
```

### 7.2 Filter 字符串构建

格式：`DimName + cDelimElemStart + Element | cDelimDim | NextDim + cDelimElemStart + Element`

多值元素用 `cDelimElement` 分隔：
```ti
sFilter = '';
sFilter = 'Scenario' | cDelimElemStart | cScenario;
sFilter = sFilter | cDelimDim | 'Version' | cDelimElemStart | cVersion;
sFilter = sFilter | cDelimDim | 'Data Source' | cDelimElemStart | cDataSourceTgt01 | cDelimElement | cDataSourceTgt02;
```

### 7.3 临时 View/Subset 命名

```ti
cTempName = '}TI_' | cProcessName | NumberToString(Int(Rand() * 10000));
While (ViewExists(cCubeSource, cTempName) <> 0);
    cTempName = '}TI_' | cProcessName | NumberToString(Int(Rand() * 10000));
End;
cView = cTempName;
cSub = cView;  # Subset 与 View 同名
```

### 7.4 使用 }Bedrock 库创建 View 和清理数据

```ti
# 创建数据源 View
ExecuteProcess('}bedrock.cube.view.create',
   'pLogOutput', 1,
   'pCube', cCubeSource,
   'pView', cView,
   'pFilter', sFilter,
   'pSuppressZero', 1,
   'pSuppressConsol', 1,
   'pSuppressRules', 1,
   'pDimDelim', cDelimDim,
   'pEleStartDelim', cDelimElemStart,
   'pEleDelim', cDelimElement,
   'pTemp', 0,
   'pSubN', 0
  );

# 清理目标数据
ExecuteProcess('}bedrock.cube.data.clear',
   'pLogOutput', 0,
   'pCube', cCubeTarget,
   'pView', '',
   'pFilter', sFilter,
   'pFilterParallel', '',
   'pParallelThreads', 0,
   'pDimDelim', cDelimDim,
   'pEleStartDelim', cDelimElemStart,
   'pEleDelim', cDelimElement,
   'pCubeLogging', 0,
   'pTemp', 1
  );
```

### 7.5 MDX 方式构建 Subset Assign to View（备选方案）

```ti
sDim = 'Scenario';
mdx = '{[Scenario].[ACT]}';
SubsetCreatebyMDX(cSubClr, mdx, sDim, 1);
ViewSubsetAssign(cCubSrc, cView, sDim, cSubClr);
```

### 7.6 View 提取设置

```ti
ViewExtractSkipCalcsSet(cCubSrc, cView, 1);       # 跳过聚合节点
ViewExtractSkipRuleValuesSet(cCubSrc, cView, 1);   # 跳过规则计算值
ViewExtractSkipZeroesSet(cCubSrc, cView, 1);       # 跳过零值
```

### 7.7 临时对象清理（Epilog）

```ti
If ( ViewExists(cCubeSource, cView) <> 0 );
  ExecuteProcess('}bedrock.cube.viewandsubsets.delete',
     'pLogOutput', 0,
     'pCube', cCubeSource,
     'pView', cView,
     'pSub', cView,
     'pMode', 1
    );
EndIf;
```

---

## 八、数据加载最佳实践

### 8.1 关闭 Cube Logging（大数据加载时）

```ti
# Prolog: 关闭日志提升性能
sTM1_transactionLog = CellGetS('}CubeProperties', cCubeTarget, 'LOGGING');
CellPutS('NO', '}CubeProperties', cCubeTarget, 'LOGGING');

# Epilog: 恢复日志
CellPutS(sTM1_transactionLog, '}CubeProperties', cCubeTarget, 'LOGGING');
```

### 8.2 使用 CellIncrementN 而非 CellPutN（Cube-to-Cube 迁移）

当多个 Process 可能向同一 Cell 写入数据时，使用 `CellIncrementN` 避免覆盖：
```ti
CellIncrementN(vValue, cCubeTarget, cScenario, cVersion, vYear, vMonth, sBU, sItem, vSource, sDataSource, cReference, cMeasure);
```

### 8.3 Mapping 模式（属性查找 + 默认值降级）

对每个需要映射的维度，使用统一的三段式模式：
```ti
# Target Dimension Mapping
sDim = 'Target Dim';
sEle = CellGetS(cAttributeCube, vSourceElement, 'AttributeName');
sEleDefault = 'No Element';
IF(DIMIX(sDim, sEle) = 0);
  sEle = sEleDefault;
ENDIF;
sVariableName = sEle;
```

### 8.4 维度层次结构构建模式

```
1. 检查并创建根合并元素（cConsol）
2. 检查并创建默认元素（cEleDefault）
3. 将默认元素挂载到根合并元素下
4. 检查并插入子元素
5. 如果存在父元素，检查并插入父元素，建立父子关系
6. 将 N 级子元素挂载到根合并元素下
```

---

## 九、其他约定

### 9.1 时间戳和随机数

```ti
sTimeStamp = TimSt( Now, '\Y\m\d\h\i\s' );
sRandomInt = NumberToString( INT( RAND( ) * 1000 ));
```

### 9.2 系统配置 Cube 读取

从系统参数 Cube 读取配置而非硬编码路径：
```ti
cCubParam = '}APQ Settings';
cCubSysParam = 'Sys Parameter';
cViewSrcPrefix = CellGetS( cCubParam, 'Std Datasource View Prefix', 'String' );
cFilePath = CellGetS( cCubSysParam, 'TM1 Source Data Directory', 'Text' );
```



### 9.3 使用 ExecuteProcess 调用其他 Process

调用 Bedrock 库或其他 Process 时，参数按名值对传入：
```ti
ExecuteProcess('}bedrock.hier.unwind.new',
    'pDim', cDim,
    'pConsol', '*',
    'pRecursive', 1
);

ExecuteProcess(sProc,
   'pScenario', pScenario,
   'pVersion', pVersion,
   'pYearFiscal', cYearFiscal,
   'pMonthFiscal', cMonthFiscal
);
```

### 9.4 Expand 函数的两种参数记录方式

```ti
# 方式一：使用 Expand
sProcLogParams = Expand( 'pParam1:%pParam1% & pParam2:%pParam2%' );

# 方式二：使用管道符拼接
sProcLogParams = 'pParam1:' | pParam1 | ' & ' | 'pParam2:' | pParam2;
```

两种方式均可，选择一种并在同一个 Process 中保持一致。

### 9.5 维度排序

```ti
DimensionSortOrder(cDim, 'ByName', 'Ascending', 'ByHierarchy', 'Ascending');
```
