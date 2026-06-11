# TI Process 案例代码

本文件包含三个典型 TI Process 示例，供生成 TI 代码时参考。

| 示例 | 场景 | 数据源类型 | 目标类型 |
|------|------|-----------|---------|
| 示例 1 | Cube 到 Cube 数据导入（含映射转换与链式调用） | Cube View | Cube |
| 示例 2 | CSV 文件数据加载到 Cube | ASCII (CSV) | Cube |
| 示例 3 | ODBC 数据库构建层级维度及属性 | ODBC (存储过程) | Dimension |

---

## 示例 1：Cube-to-Cube 数据导入（View 数据源）

**功能描述**：将 STG Cube 数据导入到 Report Cube，通过映射 Cube 转换报表科目，Epilog 中链式调用后续计算流程。

**数据源类型**：Cube View
**数据源**：`ZL Sales Payments Data STG`
**目标类型**：Cube
**目标对象**：`ZL Sales Payments Data Report`

### Prolog

```turbointegrator
################################################################
### DatasourceType:     Cube
### Datasource:         ZL Sales Payments Data STG
### Target objectType : Cube
### Datatarget:         ZL Sales Payments Data Report
################################################################
### Date          Create        Purpose
### 2022/4/16     author        将 STG Cube 的数据导入到 Report Cube 中
################################################################

### Logging - common script  ----------------- START (CUBEWISE APLIQODE FRAMEWORK)
sThisProcName = GetProcessName();
### Params
sProcLogParams = 'pYear:' | pYear;
sProcLogParams = sProcLogParams | ' & ' | 'pMonth:' | pMonth;

IF(pDoProcessLogging @= '1');
  IF(sProcLogParams @<>'');
    LogOutput('INFO', sThisProcName | ' run with parameters ' | sProcLogParams);
  EndIF;
  cCubTgt = '';
  sProcLogCube = '}APQ Process Execution Log';
  sCubLogCube = '}APQ Cube Last Updated by Process';
  nProcessStartTime = Now();
  nProcessFinishTime = 0;
  nMetaDataRecordCount = 0;
  nDataRecordCount = 0;
  NumericGlobalVariable('PrologMinorErrorCount');
  PrologMinorErrorCount = 0;
  NumericGlobalVariable('MetadataMinorErrorCount');
  MetadataMinorErrorCount = 0;
  NumericGlobalVariable('DataMinorErrorCount');
  DataMinorErrorCount = 0;
  NumericGlobalVariable('ProcessReturnCode');
  ProcessReturnCode = 0;
  sProcessErrorLogFile = '';
  sProcessRunBy = TM1User();
  IF(DimIx('}Clients', sProcessRunBy) > 0);
    sProcessRunBy = IF(AttrS('}Clients', sProcessRunBy, '}TM1_DefaultDisplayValue') @= '',
      sProcessRunBy, AttrS('}Clients', sProcessRunBy, '}TM1_DefaultDisplayValue'));
  EndIF;
  sLogYear = TimSt(nProcessStartTime, '\Y');
  sLogDay = TimSt(nProcessStartTime, '\m-\d');
  sLogMinute = TimSt(nProcessStartTime, '\h:\i');
  sLogSecond = TimSt(nProcessStartTime, '\s');
  IF(DimIx('}APQ Processes', sThisProcName) = 0);
    ExecuteProcess('}APQ.Dim.ControlDimensionCopies.Update',
      'pDoProcessLogging', pDoProcessLogging, 'pClear', '0');
  EndIF;
  nProcessExecutionIndex = CellGetN(sProcLogCube,
    'Total APQ Time Year', 'Total Year', 'Total Day', 'Total Minute',
    sThisProcName, 'nProcessStartedFlag') + 1;
  nProcessExecutionIntraDayIndex = CellGetN(sProcLogCube,
    sLogYear, sLogDay, 'Total Day', 'Total Minute',
    sThisProcName, 'nProcessStartedFlag') + 1;
  sYear01 = sLogYear; sYear02 = sLogYear;
  sDay01 = sLogDay; sDay02 = 'D000';
  sMinute01 = sLogMinute; sMinute02 = 'Total Day Entry';
  sSecond01 = sLogSecond; sSecond02 = 'Last Entry';
  nCountTime = 1; nTotalLogTime = 2;
  While(nCountTime <= nTotalLogTime);
    sLoggingYear = Expand('%sYear' | NumberToStringEx(nCountTime, '00', '', '') | '%');
    sLoggingDay = Expand('%sDay' | NumberToStringEx(nCountTime, '00', '', '') | '%');
    sLoggingMinute = Expand('%sMinute' | NumberToStringEx(nCountTime, '00', '', '') | '%');
    sLoggingSecond = Expand('%sSecond' | NumberToStringEx(nCountTime, '00', '', '') | '%');
    CellPutN(nProcessStartTime, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'nProcessStartTime');
    CellPutN(1, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'nProcessStartedFlag');
    CellPutN(nProcessExecutionIndex, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'nProcessExecutionIndex');
    CellPutN(nProcessExecutionIntraDayIndex, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'nProcessExecutionIntraDayIndex');
    CellPutS(sProcessRunBy, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'sRunBy');
    CellPutS(sProcLogParams, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'sParams');
    nCountTime = nCountTime + 1;
  End;
EndIF;
IF(CellGetN('}APQ Process Parallelization Control', sThisProcName, 'Disabled') <> 0);
  ProcessQuit;
EndIF;
### Logging - common script  ----------------- END (CUBEWISE APLIQODE FRAMEWORK)

######### Prolog commences
cTim = TimSt(Now(), '\Y\m\d\h\i\s');
cInt = Numbertostring(Int(Rand() * 10000));
cProName = GetProcessName();
cViewSource = '}TI' | cProName | '_' | cInt | '_' | cTim;
cSubSource = cViewSource;
cSysCube = 'Sys Parameter';
cSysType = 'Text';
cOutputFolder = CellGetS(cSysCube, 'Server Export Folder', cSysType);
cErrLogFile = CellGetS(cSysCube, 'Server Log Folder', cSysType);
cOutputFullName = cOutputFolder | cProName | '_data_debug.csv';
nErr = 0;
sErr = '';

cCubSource = 'ZL Sales Payments Data STG';
cCubTarget = 'ZL Sales Payments Data Report';
cCubRPTMap = 'Sys Definition ZL Mgt Item Mapping Input';

cSAYear = pSAYear;
cSAMonth = pSAMonth;
sSAMonthIdx00 = Subst(cSAMonth, 2, 2);
cScenario = pScenario;
cVersion = pVersion;
cMsrEle = 'Amount';
cDS = 'Base';
nProcessReturnCode01 = 0;

################################################################
### Test parameter
sYearDim = 'SA Year';
IF(DimIx(sYearDim, cSAYear) = 0);
  nErr = nErr + 1;
  sErr = 'Element "' | cSAYear | '" Not Exists in ' | sYearDim
       | ' Dimension, Please Check Your Parameter';
  ProcessBreak;
EndIF;

sMonthDim = 'SA Month';
IF(DimIx(sMonthDim, sSAMonthIdx00) = 0);
  nErr = nErr + 1;
  sErr = 'Element "' | cSAMonth | '" Not Exists in ' | sMonthDim
       | ' Dimension, Please Check Your Parameter';
  ProcessBreak;
EndIF;

################################################################
### Close transaction log temporarily and define bedrock filter delimiters
sLog = CellGetS('}CubeProperties', cCubTarget, 'LOGGING');
CellPutS('NO', '}CubeProperties', cCubTarget, 'LOGGING');

cDelimDim = Char(176);
cDelimEleStart = Char(177);
cDelimEle = Char(178);

################################################################
### Clear Target slice
sFilter = '';
sFilter = sYearDim | cDelimEleStart | pSAYear;
sFilter = sFilter | cDelimDim | sMonthDim | cDelimEleStart | cSAMonth;
sFilter = sFilter | cDelimDim | 'Scenario' | cDelimEleStart | cScenario;
sFilter = sFilter | cDelimDim | 'Version' | cDelimEleStart | cVersion;
sPro = '}bedrock.cube.data.clear';
ExecuteProcess(sPro,
  'pLogOutput', 0,
  'pCube', cCubTarget,
  'pView', cViewSource,
  'pFilter', sFilter,
  'pFilterParallel', '',
  'pParallelThreads', 0,
  'pDimDelim', cDelimDim,
  'pEleStartDelim', cDelimEleStart,
  'pEleDelim', cDelimEle,
  'pCubeLogging', 0,
  'pTemp', 1,
  'pSandbox', '');
### End Clear Data

################################################################
### Create source View
sFilter = '';
sFilter = sYearDim | cDelimEleStart | 'Year Rollup';
sFilter = sFilter | cDelimDim | 'Scenario' | cDelimEleStart | cScenario;
sFilter = sFilter | cDelimDim | 'Version' | cDelimEleStart | cVersion;
sPro = '}bedrock.cube.view.create';
ExecuteProcess(sPro,
  'pLogOutput', 0,
  'pCube', cCubSource,
  'pView', cViewSource,
  'pFilter', sFilter,
  'pSuppressZero', 1,
  'pSuppressConsol', 1,
  'pSuppressRules', 1,
  'pDimDelim', cDelimDim,
  'pEleStartDelim', cDelimEleStart,
  'pEleDelim', cDelimEle,
  'pTemp', 1,
  'pSubN', 0);

### Adjust view subset for "SA Year" — filter to leaf descendants of target year
sDim = sYearDim;
sSub = cSubSource;
sMDX = '{
  Tm1FilterByLevel(
    {Descendants({[' | sDim | '].[' | sDim | '].[' | cSAYear | ']})},
    0
  )
}';
IF(HierarchySubsetExists(sDim, sDim, sSub) = 0);
  SubsetCreatebyMDX(sSub, sMDX);
Else;
  HierarchySubsetDeleteAllElements(sDim, sDim, sSub);
  HierarchySubsetMDXSet(sDim, sDim, sSub, sMDX);
EndIF;
ViewSubsetAssign(cCubSource, cViewSource, sDim, sSub);

### Adjust view subset for "SA Month" — filter to leaf descendants of target month
sDim = sMonthDim;
sSub = cSubSource;
sMDX = '{
  Tm1FilterByLevel(
    {Descendants({[' | sDim | '].[' | sDim | '].[' | cSAMonth | ']})},
    0
  )
}';
IF(HierarchySubsetExists(sDim, sDim, sSub) = 0);
  SubsetCreatebyMDX(sSub, sMDX);
Else;
  HierarchySubsetDeleteAllElements(sDim, sDim, sSub);
  HierarchySubsetMDXSet(sDim, sDim, sSub, sMDX);
EndIF;
ViewSubsetAssign(cCubSource, cViewSource, sDim, sSub);

### End Create View
DataSourceType = 'View';
DatasourceNameForServer = cCubSource;
DatasourceNameForClient = cCubSource;
DatasourceCubeView = cViewSource;
nLineCount = 0;
######### End Prolog
```

### Metadata

```turbointegrator
### (empty — no dimension operations needed for cube-to-cube transfer)
```

### Data

```turbointegrator
######### Data commences
vComp = vCOACompany;

### Map STG measure to report item via mapping cube
vZLRptItem = CellGetS(cCubRPTMap, vSAYear, vSAMonth, vBehavior, vSTGMeasure, 'ZL Mgt Report Item');
IF(vBehavior @<> '' & vSTGMeasure @<> ''
    & (vZLRptItem @= '' % vZLRptItem @= 'null' % vZLRptItem @= '\r\n'));
  nErr = nErr + 1;
  sErr = 'Warning: Behavior=' | vBehavior | ', Measure=' | vSTGMeasure
       | ', Can not get any ZL Mgt Report Item, Please Check your Map Cube';
  ProcessBreak;
EndIF;

### Load data to target cube
CellIncrementN(vValue, cCubTarget,
  cScenario, vSAYear, vSAMonth, cVersion,
  vComp, vCurrency, vCountry, vProduct, vPlatform,
  vZLRptItem, cDS, cMsrEle);

### (Optional) Debug CSV output
# SetOutputCharacterSet(cOutputFullName, 'TM1CS_UTF8');
# TextOutput(cOutputFullName, NumberToString(vValue),
#   cScenario, vSAYear, vSAMonth, cVersion,
#   vComp, vCurrency, vCountry, vProduct, vPlatform,
#   vBehavior, vSTGMeasure, vZLRptItem);

nLineCount = nLineCount + 1;
######### End Data
```

### Epilog

```turbointegrator
######### Epilog commences
### Restore transaction logging
CellPutS(sLog, '}CubeProperties', cCubTarget, 'LOGGING');

### Clean up temporary view and subsets
IF(ViewExists(cCubSource, cViewSource) <> 0);
  ExecuteProcess('}bedrock.cube.viewandsubsets.delete',
    'pLogOutput', 0,
    'pCube', cCubSource,
    'pView', cViewSource,
    'pSub', cSubSource,
    'pMode', 1);
EndIF;

### Chain: invoke currency calculation process after data load
sPro = 'SalesPaymentsReport.Currency.Cal';
sParam1 = 'pSAYear';    sParaVal1 = cSAYear;
sParam2 = 'pSAMonth';   sParaVal2 = cSAMonth;
sParam3 = 'pScenario';  sParaVal3 = cScenario;
sParam4 = 'pVersion';   sParaVal4 = cVersion;
sParam5 = 'pOU';        sParaVal5 = 'OU_DEFAULT';
sParam6 = 'pCountry';   sParaVal6 = 'All Country List';
sParam7 = 'pZLRptItem'; sParaVal7 = 'All Rpt Item';
nProcessReturnCode01 = ExecuteProcess(sPro,
  sParam1, sParaVal1, sParam2, sParaVal2, sParam3, sParaVal3,
  sParam4, sParaVal4, sParam5, sParaVal5, sParam6, sParaVal6,
  sParam7, sParaVal7);
IF(nProcessReturnCode01 <> 0);
  nErr = nErr + 1;
  sErr = '';
  LogOutput('Error', 'Process: "' | sPro | '" Failed, Exit Code: '
    | NumberToString(nProcessReturnCode01));
  ProcessQuit;
EndIF;

### Error handling
IF(nErr <> 0);
  LogOutput('Error', sErr);
  ProcessQuit;
EndIF;

### Logging - common script  ----------------- END (CUBEWISE APLIQODE FRAMEWORK)
IF(pDoProcessLogging @= '1');
  nProcessFinishTime = Now();
  sProcessErrorLogFile = GetProcessErrorFileName;
  sYear01 = sLogYear; sYear02 = sLogYear;
  sDay01 = sLogDay; sDay02 = 'D000';
  sMinute01 = sLogMinute; sMinute02 = 'Total Day Entry';
  sSecond01 = sLogSecond; sSecond02 = 'Last Entry';
  nCountTime = 1; nTotalLogTime = 2;
  While(nCountTime <= nTotalLogTime);
    sLoggingYear = Expand('%sYear' | NumberToStringEx(nCountTime, '00', '', '') | '%');
    sLoggingDay = Expand('%sDay' | NumberToStringEx(nCountTime, '00', '', '') | '%');
    sLoggingMinute = Expand('%sMinute' | NumberToStringEx(nCountTime, '00', '', '') | '%');
    sLoggingSecond = Expand('%sSecond' | NumberToStringEx(nCountTime, '00', '', '') | '%');
    CellPutN(nProcessFinishTime, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'nProcessFinishTime');
    CellPutN(1, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'nProcessCompletedFlag');
    CellPutN(nMetaDataRecordCount, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'nMetaDataRecordCount');
    CellPutN(nDataRecordCount, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'nDataRecordCount');
    CellPutN(PrologMinorErrorCount, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'nPrologMinorErrorCount');
    CellPutN(MetadataMinorErrorCount, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'nMetaDataMinorErrorCount');
    CellPutN(DataMinorErrorCount, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'nDataMinorErrorCount');
    CellPutN(ProcessReturnCode, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'nProcessReturnCode');
    CellPutS(sProcessErrorLogFile, sProcLogCube, sLoggingYear, sLoggingDay,
      sLoggingMinute, sLoggingSecond, sThisProcName, 'sProcessErrorLogFile');
    nCountTime = nCountTime + 1;
  End;
  IF(nDataRecordCount > 0);
    IF(cCubTgt @<>'');
      CellPutN(nProcessFinishTime, sCubLogCube, cCubTgt, 'nLastTimeUpdate');
      CellPutS(sThisProcName, sCubLogCube, cCubTgt, 'sProcess');
      CellPutS(sProcessRunBy, sCubLogCube, cCubTgt, 'sProcessRunBy');
    EndIF;
  EndIF;
EndIF;
### End Epilog
```

---

## 示例 2：CSV 数据加载到 Cube

**功能描述**：从服务器目录搜索 CSV 文件，按通配符匹配后读取数据写入目标 Cube。

**数据源类型**：ASCII (Character Delimited)
**数据源文件**：`sys_lookup_year_month*.csv`（支持通配符）
**目标类型**：Cube
**目标对象**：`Sys Lookup Year Month`

### Prolog

```turbointegrator
################################################################
### DatasourceType:     CSV
### Datasource:         sys_lookup_year_month.csv
### Target objectType : Cube
### Datatarget:         Sys Lookup Year Month
################################################################
### Date          Create        Purpose
### 2022/6/18     author        Load data from csv to cube
################################################################
cThisProcessName = GetProcessName();
cLogInfo = 'Process:%cThisProcessName% run with parameters '
         | 'pSAYear:%pSAYear%, pSAMonth:%pSAMonth%, '
         | 'pScenario:%pScenario%, pVersion:%pVersion%.';
cLogInfo = Expand(cLogInfo);

######### Prolog commences
cProExeStartTim = Now();
cTim = TimSt(Now(), '\Y\m\d\h\i\s');
cInt = Numbertostring(Int(Rand() * 10000));
cThisProcessName = GetProcessName();
cViewSource = '}TI_' | cThisProcessName | '_' | cTim | '_' | cInt;
cSubSource = cViewSource;
cSysCube = 'Sys Parameter';
cSysType = 'Text';
cOutputFolder = CellGetS(cSysCube, 'Server Export Folder', cSysType);
cImportFolder = CellGetS(cSysCube, 'Server Import Folder', cSysType);

nErr = 0;
sErr = '';
cCubTarget = 'Sys Lookup Year Month';
cFileName = 'sys_lookup_year_month*.csv';
cSAYear = pSAYear;
cSAMonth = pSAMonth;
sSAMonthIdx00 = Subst(cSAMonth, 2, 2);
cScenario = pScenario;
cVersion = pVersion;
cMsrEle = '';
cDS = '';

################################################################
### Test parameter
sDim = 'SA Year';
IF(DimIx(sDim, cSAYear) = 0);
  nErr = nErr + 1;
  sErr = 'Element "' | cSAYear | '" Not Exists in ' | sDim
       | ' Dimension, Please Check Your Parameter';
  ProcessBreak;
EndIF;

sDim = 'SA Month';
IF(DimIx(sDim, cSAMonth) = 0);
  nErr = nErr + 1;
  sErr = 'Element "' | cSAMonth | '" Not Exists in ' | sDim
       | ' Dimension, Please Check Your Parameter';
  ProcessBreak;
EndIF;

################################################################
### Search for CSV source file
sFileName = WildcardFileSearch(cImportFolder | cFileName, '');
sFileFullName = cImportFolder | sFileName;
LogOutput('info', sFileFullName);
IF(FileExists(sFileFullName) = 0 % cFileName @<>'');
  nErr = nErr + 1;
  sErr = 'Source File: "' | cFileName | '" ,Can not be found in designated Folder, Please Check Your Folder';
  ProcessBreak;
EndIF;
LogOutput('info', sFileFullName);

################################################################
### Close transaction log temporarily and define bedrock filter delimiters
sLog = CellGetS('}CubeProperties', cCubTarget, 'LOGGING');
CellPutS('NO', '}CubeProperties', cCubTarget, 'LOGGING');

cDelimDim = Char(176);
cDelimEleStart = Char(177);
cDelimEle = Char(178);

################################################################
### Clear Target slice
sFilter = '';
sFilter = 'Year Month' | cDelimEleStart | cSAYear | ' ' | cSAMonth;
sPro = '}bedrock.cube.data.clear';
ExecuteProcess(sPro,
  'pLogOutput', 0,
  'pCube', cCubTarget,
  'pView', cViewSource,
  'pFilter', sFilter,
  'pFilterParallel', '',
  'pParallelThreads', 0,
  'pDimDelim', cDelimDim,
  'pEleStartDelim', cDelimEleStart,
  'pEleDelim', cDelimEle,
  'pCubeLogging', 0,
  'pTemp', 1,
  'pSandbox', '');
### End Clear Data

### Set datasource
DataSourceType = 'Characterdelimited';
DatasourceNameForServer = sFileFullName;
DatasourceAsciiHeaderRecords = 1;
nLineCount = 0;
######### End Prolog
```

### Metadata

```turbointegrator
### (empty — no dimension operations needed for CSV-to-Cube load)
```

### Data

```turbointegrator
######### Data commences
sVal = vValue;

### Write data to target cube (check cell is updateable first)
IF(CellIsUpdateable(cCubTarget, vYearMonth, vYearMonthIndex, vMeasure) > 0);
  CellPutS(sVal, cCubTarget, vYearMonth, vYearMonthIndex, vMeasure);
EndIF;

nLineCount = nLineCount + 1;
######### End Data
```

### Epilog

```turbointegrator
######### Epilog commences
### Restore transaction logging
CellPutS(sLog, '}CubeProperties', cCubTarget, 'LOGGING');

### Error handling
IF(nErr <> 0);
  LogOutput('Error', sErr);
  ProcessQuit;
EndIF;
######### End Epilog
```

---

## 示例 3：ODBC 维度更新（从数据库构建层级维度）

**功能描述**：从 ERP 数据库存储过程读取科目数据，动态构建带层级结构的维度并写入属性。

**数据源类型**：ODBC
**数据源**：ERP 数据库存储过程
**目标类型**：Dimension
**目标维度**：`COA Account GL`

### Prolog

```turbointegrator
################################################################
### DatasourceType:     ODBC
### Datasource:         ERP Database stored procedure
### Target objectType : Dimension
### Datatarget:        COA Account GL
################################################################
### Date          Create        Purpose
### 2022/5/11     author        将 ERP 系统的会计科目表导入到 COA Account GL 维度中
### 数据来源可以是各种 ERP 系统的数据库或者 CSV 文件
################################################################

######### Prolog commences
cTim = TimSt(Now(), '\Y\m\d\h\i\s');
cInt = Numbertostring(Int(Rand() * 10000));
cProName = GetProcessName();
cViewSource = '}TI' | cProName | '_' | cInt | '_' | cTim;
cSubSource = cViewSource;
cSysCube = 'Sys Parameter';
cSysType = 'Text';
cOutputFolder = CellGetS(cSysCube, 'Server Export Folder', cSysType);
cErrLogFile = CellGetS(cSysCube, 'Server Log Folder', cSysType);
cOutputFullName = cOutputFolder | cProName | '_data_debug.csv';
cErrorFilename = cErrLogFile | 'TM1ProcessError_' | '*' | cProName | '.log';
nErr = 0;
sErr = '';

cTgrDim = 'COA Account GL';
cTgrDim2 = 'Account BS';
cTgrDim3 = 'Account PL';
cTgrDim4 = 'Account GL';
cSAYear = pSAYear;
cSAMonth = pSAMonth;
cSAMonthIdx00 = Subst(cSAMonth, 2, 2);

################################################################
### Test parameter
sYearDim = 'SA Year';
IF(DimIx(sYearDim, cSAYear) = 0);
  nErr = nErr + 1;
  sErr = 'Element "' | pSAYear | '" Not Exists in ' | sYearDim
       | ' Dimension, Please Check Your Parameter';
  ProcessBreak;
EndIF;

sMonthDim = 'SA Month';
IF(DimIx(sMonthDim, cSAMonthIdx00) = 0);
  nErr = nErr + 1;
  sErr = 'Element "' | pSAMonth | '" Not Exists in ' | sMonthDim
       | ' Dimension, Please Check Your Parameter';
  ProcessBreak;
EndIF;

################################################################
### Define ODBC connection variables (read from Sys Parameter cube)
cODBCSource = CellGetS(cSysCube, 'SQL Server ODBC Name', cSysType);
cUser = CellGetS(cSysCube, 'SQL Server Admin', cSysType);
cPsd = CellGetS(cSysCube, 'SQL Server Admin Psd', cSysType);
cDBName = 'ERP_DATA_DB';
cProcedureName = 'dim_account_fullname_gl_update';
cSQLMonth = cSAMonthIdx00;

### Open ODBC connection
ODBCOpen(cODBCSource, cUser, cPsd);

### Execute stored procedure to prepare source data
sSQL = 'exec [' | cDBName | '].[dbo].[' | cProcedureName | ']';
LogOutput('info', 'Data fetch period: ' | cSAYear | cSQLMonth);
LogOutput('info', 'Calling stored procedure: ' | cProcedureName | ' from ' | cDBName);
ODBCOutput(cODBCSource, sSQL);

### Set datasource to ODBC query
DataSourceType = 'ODBC';
DatasourceNameForServer = cODBCSource;
DatasourceNameForClient = cODBCSource;
DatasourceUserName = cUser;
DatasourcePassword = cPsd;
DatasourceQuery = sSQL;
nLineCount = 0;
######### End Prolog
```

### Metadata

```turbointegrator
######### Metadata commences

### Define variable for element insertion
vAccountCode = vCode;

### Build dimension hierarchy — nested Level0 to Level4 with parent-child edges
IF(vLevel0 @<> 'null' & vLevel0 @<> '' & vLevel0 @<> '\r\n');
  DimensionElementInsertDirect(cTgrDim, '', vLevel0, 'N');
  IF(vLevel1 @<> 'null' & vLevel1 @<> '' & vLevel1 @<> '\r\n');
    DimensionElementInsertDirect(cTgrDim, '', vLevel1, 'N');
    DimensionElementComponentAddDirect(cTgrDim, vLevel1, vLevel0, 1);
    IF(vLevel2 @<> 'null' & vLevel2 @<> '' & vLevel2 @<> '\r\n');
      DimensionElementInsertDirect(cTgrDim, '', vLevel2, 'N');
      DimensionElementComponentAddDirect(cTgrDim, vLevel2, vLevel1, 1);
      IF(vLevel3 @<> 'null' & vLevel3 @<> '' & vLevel3 @<> '\r\n');
        DimensionElementInsertDirect(cTgrDim, '', vLevel3, 'N');
        DimensionElementComponentAddDirect(cTgrDim, vLevel3, vLevel2, 1);
        IF(vLevel4 @<> 'null' & vLevel4 @<> '' & vLevel4 @<> '\r\n');
          DimensionElementInsertDirect(cTgrDim, '', vLevel4, 'N');
          DimensionElementComponentAddDirect(cTgrDim, vLevel4, vLevel3, 1);
        EndIF;
      EndIF;
    EndIF;
  EndIF;
EndIF;

### Add all leaf elements under root consolidation "All GL Accounts"
cEle = 'All GL Accounts';
IF(DType(cTgrDim, vAccountCode) @= 'N');
  IF(ElIsPar(cTgrDim, cEle, vAccountCode) = 0);
    DimensionElementComponentAddDirect(cTgrDim, cEle, vAccountCode, 1);
  EndIF;
EndIF;

### End Metadata
```

### Data

```turbointegrator
######### Data commences

### Write element attributes to the dimension
vAccountCode = vCode;
vAccountName = vCodeName;
vEle = vAccountCode;
sTgrDim = cTgrDim;
vAttrName = 'Description';
AttrPutS(vAccountName, sTgrDim, vEle, vAttrName, '', 1);

### End Data
```

### Epilog

```turbointegrator
######### Epilog commences

### Close ODBC connection
ODBCClose(cODBCSource);

### Error handling
IF(nErr <> 0);
  LogOutput('Error', sErr);
  ProcessQuit;
EndIF;

### End Epilog
```
