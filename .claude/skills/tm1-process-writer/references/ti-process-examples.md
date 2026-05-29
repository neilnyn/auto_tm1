# TI Process 案例代码
> ### 示例 1：[example01]
> **功能描述**：[cube A的数据导入到cube A并挂载后续脚本]
>
> #### Prolog
> ```
################################################################
### DatasourceType:     Cube
### Datasource:         ZL Amazon Payments Data STG
### Target objectType : Cube
### Datatarget:         ZL Amazon Payments Data Report
###############################################################################################################################
### Date          Create        Purpose
### 2022/4/16     neil      将ZL Amazon Payments Data STG的数据导入到ZL Amazon Payments Data Report 中
###############################################################################################################################
### Logging - common script 	----------------- START (CUBEWISE APLIQODE FRAMEWORK)
sThisProcName = GetProcessName();
### Params
sProcLogParams = 'pYear:' | pYear ;
sProcLogParams =  sProcLogParams | ' & ' | 'pMonth:' | pMonth;
# E.g.1 sProcLogParams = Expand( 'pParam1:%pParam1% & pParam2:%pParam2% & pParam3:%pParam3% & pParamN:%pParamN%' );
# E.g.2 sProcLogParams = 'pParam1:' | pParam1 |' & '| 'pParam2:' | pParam2 |' & '| 'pParam3:' | pParam3 |' & '| 'pParamN:' | pParamN;
### Params
IF( pDoProcessLogging @= '1' ); IF( sProcLogParams @<> '' ); LogOutput( 'INFO', sThisProcName | ' run with parameters ' | sProcLogParams ); EndIF;
  cCubTgt = ''; sProcLogCube = '}APQ Process Execution Log'; sCubLogCube = '}APQ Cube Last Updated by Process'; nProcessStartTime = Now(); nProcessFinishTime = 0; nMetaDataRecordCount = 0; nDataRecordCount = 0;
  NumericGlobalVariable( 'PrologMinorErrorCount' );  PrologMinorErrorCount = 0; NumericGlobalVariable( 'MetadataMinorErrorCount' );  MetadataMinorErrorCount = 0; NumericGlobalVariable( 'DataMinorErrorCount' );  DataMinorErrorCount = 0; NumericGlobalVariable( 'ProcessReturnCode' );  ProcessReturnCode = 0;
  sProcessErrorLogFile = ''; sProcessRunBy = TM1User(); IF( DimIx( '}Clients', sProcessRunBy ) > 0 ); sProcessRunBy = IF( AttrS( '}Clients', sProcessRunBy, '}TM1_DefaultDisplayValue' ) @= '', sProcessRunBy, AttrS( '}Clients', sProcessRunBy, '}TM1_DefaultDisplayValue' ) ); EndIF;
  sLogYear = TimSt( nProcessStartTime, '\Y' ); sLogDay = TimSt( nProcessStartTime, '\m-\d' ); sLogMinute = TimSt( nProcessStartTime, '\h:\i' ); sLogSecond = TimSt( nProcessStartTime, '\s' ); IF( DimIx( '}APQ Processes', sThisProcName ) = 0 ); ExecuteProcess( '}APQ.Dim.ControlDimensionCopies.Update', 'pDoProcessLogging', pDoProcessLogging, 'pClear', '0' ); EndIF;
  nProcessExecutionIndex = CellGetN( sProcLogCube, 'Total APQ Time Year', 'Total Year', 'Total Day', 'Total Minute', sThisProcName, 'nProcessStartedFlag' ) + 1; nProcessExecutionIntraDayIndex = CellGetN( sProcLogCube, sLogYear, sLogDay, 'Total Day', 'Total Minute', sThisProcName, 'nProcessStartedFlag' ) + 1;
  sYear01 = sLogYear; sYear02 = sLogYear; sDay01 = sLogDay; sDay02 = 'D000'; sMinute01 = sLogMinute; sMinute02 = 'Total Day Entry'; sSecond01 = sLogSecond; sSecond02= 'Last Entry'; nCountTime = 1; nTotalLogTime = 2; 
  While ( nCountTime <= nTotalLogTime ); sLoggingYear = Expand( '%sYear' | NumberToStringEx( nCountTime, '00', '', '' ) | '%' ); sLoggingDay = Expand( '%sDay' | NumberToStringEx( nCountTime, '00', '', '' ) | '%' ); sLoggingMinute = Expand( '%sMinute' | NumberToStringEx( nCountTime, '00', '', '' ) | '%' ); sLoggingSecond = Expand( '%sSecond' | NumberToStringEx( nCountTime, '00', '', '' ) | '%' );
  CellPutN( nProcessStartTime, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'nProcessStartTime' ); CellPutN( 1, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'nProcessStartedFlag' );
  CellPutN( nProcessExecutionIndex, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'nProcessExecutionIndex' ); CellPutN( nProcessExecutionIntraDayIndex, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'nProcessExecutionIntraDayIndex' );
  CellPutS( sProcessRunBy, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'sRunBy' ); CellPutS( sProcLogParams, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'sParams' ); nCountTime = nCountTime + 1; End;
EndIF; IF( CellGetN( '}APQ Process Parallelization Control', sThisProcName, 'Disabled' ) <> 0 ); ProcessQuit; EndIF;
###################################################################################################################
######### Prolog commences
cTim = TimSt( now(), '\Y\m\d\h\i\s');
cInt = Numbertostring( Int(Rand()*10000) );
cProName = Getprocessname();
cViewSource = '}TI' | cProName | '_' | cInt |'_' | cTim;
cSubSource = cViewSource;
cSysCube = 'Sys Parameter';
cSysType = 'Text';
cOutputFolder = Cellgets(cSysCube, 'Server Export Folder', cSysType);
cErrLogFile = Cellgets(cSysCube, 'Server Log Folder', cSysType);
cOutputFullName = cOutputFolder | cProName |'_data_debug.csv'; 
nErr= 0;
sErr= '';

cCubSource = 'ZL Amazon Payments Data STG';
cCubTarget = 'ZL Amazon Payments Data Report';
cCubRPTMap = 'Sys Definition ZL Mgt Item Mapping Input';

cSAYear = pSAYear;
cSAMonth = pSAMonth;
sSAMonthidx00 = Subst(cSAMonth,2,2);
cScenario = pScenario;
cVersion = pVersion;
cMsrEle = 'Amount';
cDS = 'Base';
nProcessReturnCode01=0;
##################################################################################################
### Test parameter
sYearDim = 'SA Year';
if(Dimix( sYearDim,cSAYear ) = 0);
  nErr = nErr +1;
  sErr = 'Element "' | cSAYear | '" Not Exists in ' | sYearDim | ' Dimension, Please Check Your Paramenter';
  ProcessBreak;
endif;

sMonthDim = 'SA Month';
if(Dimix( sMonthDim, sSAMonthidx00 ) = 0);
  nErr = nErr +1;
  sErr = 'Element "' | cSAMonth | '" Not Exists in ' | sMonthDim | ' Dimension, Please Check Your Paramenter';
  ProcessBreak;
endif;
##################################################################################################
### close transaction log changes temporarily and define constants for bedrock parameter Filter
sLog = Cellgets('}CubeProperties', cCubTarget, 'LOGGING');
Cellputs('NO','}CubeProperties', cCubTarget, 'LOGGING');

cDelimDim = Char(176);
cDelimEleStart = Char(177);
cDelimEle = Char(178);
########################################################################################################################
### Clear Target View
sFilter = '';
sFilter = sYearDim | cDelimEleStart | pSAYear;
sFilter = sFilter | cDelimDim | sMonthDim | cDelimEleStart | cSAMonth;
sFilter = sFilter | cDelimDim | 'Scenario' | cDelimEleStart | cScenario;
sFilter = sFilter | cDelimDim | 'Version' | cDelimEleStart |cVersion;
sPro = '}bedrock.cube.data.clear';
ExecuteProcess(sPro ,
  'pLogOutput',0,
  'pCube',cCubTarget,
  'pView',cViewSource,
  'pFilter',sFilter,
  'pFilterParallel','',
  'pParallelThreads',0,
  'pDimDelim',cDelimDim,
  'pEleStartDelim',cDelimEleStart,
  'pEleDelim',cDelimEle,
  'pCubeLogging',0,
  'pTemp',1,
  'pSandbox','');

### End Clear Data
########################################################################################################################
### Create source View
sFilter = '';
sFilter = sYearDim | cDelimEleStart | 'Year Rollup';
sFilter = sFilter | cDelimDim | 'Scenario' | cDelimEleStart | cScenario;
sFilter = sFilter | cDelimDim | 'Version' | cDelimEleStart | cVersion;
sPro = '}bedrock.cube.view.create';
ExecuteProcess(sPro,
  'pLogOutput',0,
  'pCube',cCubSource,
  'pView',cViewSource,
  'pFilter',sFilter,
  'pSuppressZero',1,
  'pSuppressConsol',1,
  'pSuppressRules',1,
  'pDimDelim',cDelimDim,
  'pEleStartDelim',cDelimEleStart,
  'pEleDelim',cDelimEle,
  'pTemp',1,
  'pSubN',0);

###bedrock里写了C Level元素，会将Child 全部过滤出来，可以在后面再次调整-> SA Year
###bedrock里忘记过滤维度及元素，也可以后面进行增加和调整-> SA Month
########### adjust view's subst with dim-"SA Year" for viewsource
sDim = sYearDim;
sSub = cSubSource;
sMDX = '{
        Tm1FilterByLevel({Descendants({['|sDim|'].['|sDim|'].['|cSAYear|']})},0)
        }';
#Logoutput('info','MDX: ' | sMDX);
If(HierarchySubsetExists(sDim, sDim, sSub)=0);
  SubsetCreatebyMDX(sSub, sMDX);
Else;
  HierarchySubsetDeleteAllElements(sDim, sDim, sSub);
  HierarchySubsetMDXSet(sDim, sDim, sSub, sMDX);
Endif;
ViewSubsetAssign(cCubSource, cViewSource, sDim, sSub);

########### adjust view's subst with dim-"SA Month" for viewsource
sDim = sMonthDim;
sSub = cSubSource;
sMDX = '{
        Tm1FilterByLevel({Descendants({['|sDim|'].['|sDim|'].['|cSAMonth|']})},0)
        }';
#Logoutput('info','MDX: ' | sMDX);
If(HierarchySubsetExists(sDim, sDim, sSub)=0);
  SubsetCreatebyMDX(sSub, sMDX);
Else;
  HierarchySubsetDeleteAllElements(sDim, sDim, sSub);
  HierarchySubsetMDXSet(sDim, sDim, sSub, sMDX);
Endif;
ViewSubsetAssign(cCubSource, cViewSource, sDim, sSub);

### End Create View
###########################################################################################################################
DataSourceType='View';
DatasourceNameForServer=cCubSource;
DatasourceNameForClient=cCubSource;
DatasourceCubeView = cViewSource;
nLineCount = 0;
###################################################################################################################
######### End Prolog
> ```
>
> #### Metadata
> ```
> ```
>
> #### Data
> ```
######### Data commences
vComp =  vCOACompany;

### according the Loop "behavior + Measure", we can get "ZL Mgt Report Item" through the Mapping Cube
vZLRptItem = Cellgets(cCubRPTMap, vSAYear, vSAMonth, vBehavior, vSTGMeasure, 'ZL Mgt Report Item');
If( vBehavior @<> '' & vSTGMeasure @<> '' & (vZLRptItem @= '' % vZLRptItem @= 'null' % vZLRptItem @= '\r\n') );
  nErr = nErr + 1;
  sErr = '注意: '| 'Behavior=' |vBehavior|', '| 'Measure=' |vSTGMeasure|', Can not get any ZL Mgt Report Item, Please Check your Map Cube';
  ProcessBreak;
Endif;
###################################################################################################
### Load data to cube "ZL Amazon Payments Data Report"

CellIncrementN(vValue, cCubTarget, cScenario, vSAYear, vSAMonth,
              cVersion, vComp, vCurrency, vCountry, vProduct, vPlatform, vZLRptItem, cDS,cMsrEle);

###################################################################################################################
######### Outout csv for debug
#SetOutputCharacterSet( cOutputFullName , 'TM1CS_UTF8');
#Textoutput( cOutputFullName, Numbertostring(vValue), cScenario, vSAYear, vSAMonth, 
#              cVersion, vComp, vCurrency, vCountry, vProduct, vPlatform, vBehavior, vSTGMeasure, vZLRptItem);
  
nLineCount =  nLineCount +1;
###################################################################################################################
######### End Data
> ```
>
> #### Epilog
> ```
######### Epilog commences
### recover transaction log state
#CubeSetLogChanges(cCubTarget, cLog);
Cellputs(sLog,'}CubeProperties', cCubTarget, 'LOGGING');

#####################################################################################
### clear temporary view build in previous tab
# pMode=1,said that the view and subset will be deleted directly
If( ViewExists(cCubSource, cViewSource) <> 0);
  ExecuteProcess('}bedrock.cube.viewandsubsets.delete',
  'pLogOutput',0,
  'pCube',cCubSource,
  'pView',cViewSource,
  'pSub',cSubSource,
  'pMode',1);
Endif;
################################################################################
## Cal All Currenies after Load Data
sPro = '17A.Cub.ZL Amazon Payments Data Report.Currency.CNY.Cal';
sParam1 = 'pSAYear';    sParaVal1= cSAYear;
sParam2 = 'pSAMonth';   sParaVal2= cSAMonth;
sParam3 = 'pScenario';  sParaVal3= cScenario;
sParam4 = 'pVersion';   sParaVal4= cVersion;
sParam5 = 'pOU';        sParaVal5= '002';
sParam6 = 'pCountry';   sParaVal6= 'All Country List';
sParam7 = 'pZLRptItem'; sParaVal7= 'All Rpt Item';
nProcessReturnCode01 = ExecuteProcess(sPro,sParam1,sParaVal1,sParam2,sParaVal2,sParam3,
                        sParaVal3,sParam4,sParaVal4,sParam5,sParaVal5,sParam6,sParaVal6,sParam7,sParaVal7);
If( nProcessReturnCode01 <> 0);
  nErr = nErr+1;
  sErr = '';
  Logoutput('Error', 'Prcoess: "' |sPro|'" Failed,Exit Code is'| Numbertostring( nProcessReturnCode01 ) );
  ProcessQuit;
Endif;
#####################################################################################
### Err Handling
If(nErr <> 0);
  LogOutput('Error', sErr);
  ProcessQuit;
EndIf;



### Logging - common script 	----------------- END (CUBEWISE APLIQODE FRAMEWORK)
### ( Place as last code block on epilog )
IF( pDoProcessLogging @= '1' );
  nProcessFinishTime = Now(); sProcessErrorLogFile = GetProcessErrorFileName; sYear01 = sLogYear; sYear02 = sLogYear; sDay01 = sLogDay; sDay02 = 'D000'; sMinute01 = sLogMinute; sMinute02 = 'Total Day Entry'; sSecond01 = sLogSecond; sSecond02= 'Last Entry'; nCountTime = 1; nTotalLogTime = 2; 
  While( nCountTime <= nTotalLogTime );    sLoggingYear = Expand( '%sYear' | NumberToStringEx( nCountTime, '00', '', '' ) | '%' ); sLoggingDay = Expand( '%sDay' | NumberToStringEx( nCountTime, '00', '', '' ) | '%' ); sLoggingMinute = Expand( '%sMinute' | NumberToStringEx( nCountTime, '00', '', '' ) | '%' ); sLoggingSecond = Expand( '%sSecond' | NumberToStringEx( nCountTime, '00', '', '' ) | '%' );
  CellPutN( nProcessFinishTime, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'nProcessFinishTime' ); CellPutN( 1, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'nProcessCompletedFlag' );
  CellPutN( nMetaDataRecordCount, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'nMetaDataRecordCount' ); CellPutN( nDataRecordCount, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'nDataRecordCount' );
  CellPutN( PrologMinorErrorCount, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'nPrologMinorErrorCount' ); CellPutN( MetadataMinorErrorCount, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'nMetaDataMinorErrorCount' );
  CellPutN( DataMinorErrorCount, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'nDataMinorErrorCount' ); CellPutN( ProcessReturnCode, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'nProcessReturnCode' );
  CellPutS( sProcessErrorLogFile, sProcLogCube, sLoggingYear, sLoggingDay, sLoggingMinute, sLoggingSecond, sThisProcName, 'sProcessErrorLogFile' );  nCountTime = nCountTime + 1; End;
  IF( nDataRecordCount > 0 ); IF( cCubTgt @<> '' ); CellPutN( nProcessFinishTime, sCubLogCube, cCubTgt, 'nLastTimeUpdate' ); CellPutS( sThisProcName, sCubLogCube, cCubTgt, 'sProcess' ); CellPutS( sProcessRunBy, sCubLogCube, cCubTgt, 'sProcessRunBy' ); EndIF; EndIF;
EndIF;
### Logging - common script 	-----------------  END
### End Epilog
> ```



> ### 示例 2：[example02]
> **功能描述**：[cube data load from csv]
>
> #### Prolog
> ```
################################################################
### DatasourceType:     CSV
### Datasource:         sys_lookup_year_month.csv
### Target objectType : Cube
### Datatarget:         Sys Lookup Year Month
###############################################################################################################################
### Date          Create        Purpose
### 2022/6/18      neil      Load data from csv to cub 
### 
###############################################################################################################################
cThisProcessName = Getprocessname();
cLogInfo = 'Process:%cThisProcessName% run with parameters pSAYear:%pSAYear%, pSAMonth:%pSAMonth%, pScenario:%pScenario%, pVersion:%pVersion%.' ; 
cLogInfo = Expand(cLogInfo);
######### Prolog commences
cProExeStartTim = Now();
cTim = TimSt( Now(), '\Y\m\d\h\i\s');
cInt = Numbertostring( Int(Rand()*10000) );
cThisProcessName = Getprocessname();
cViewSource = '}TI_' | cThisProcessName | '_' | cTim |'_' | cInt;
cSubSource = cViewSource;
cSysCube = 'Sys Parameter';
cSysType = 'Text';
cOutputFolder = Cellgets(cSysCube, 'Server Export Folder', cSysType);
cImportFolder = Cellgets(cSysCube, 'Server Import Folder', cSysType);

nErr= 0;
sErr= '';
cCubTarget = 'Sys Lookup Year Month';
cFileName = 'sys_lookup_year_month*.csv';
cSAYear = pSAYear;
cSAMonth = pSAMonth;
sSAMonthidx00 = Subst(cSAMonth,2,2);
cScenario = pScenario;
cVersion = pVersion;
cMsrEle = '';
cDS = '';
##################################################################################################
### Test parameter
sDim = 'SA Year';
If(Dimix( sDim,cSAYear ) = 0);
  nErr = nErr +1;
  sErr = 'Element "' | cSAYear | '" Not Exists in ' | sDim | ' Dimension, Please Check Your Paramenter';
  ProcessBreak;
Endif;

sDim = 'SA Month';
If(Dimix( sDim, cSAMonth ) = 0);
  nErr = nErr +1;
  sErr = 'Element "' | cSAMonth | '" Not Exists in ' | sDim | ' Dimension, Please Check Your Paramenter';
  ProcessBreak;
Endif;
##################################################################################################
### Search for CsvSource File, is not exist shoule give error
sFileName = WildcardFileSearch( cImportFolder | cFileName, '');
sFileFullName = cImportFolder | sFileName;
Logoutput('info',sFileFullName );
If( FileExists( sFileFullName ) = 0 % cFileName @<> '' );
  nErr = nErr + 1;
  sErr = 'Source File: "' |cFileName|'" ,Can not be found in designated Folder, Please Check Your Folder' ;
  ProcessBreak;
Endif;
Logoutput('info',sFileFullName );

##################################################################################################
### close transaction log changes temporarily and define constants for bedrock parameter Filter
sLog = Cellgets('}CubeProperties', cCubTarget, 'LOGGING');
Cellputs('NO','}CubeProperties', cCubTarget, 'LOGGING');

cDelimDim = Char(176);
cDelimEleStart = Char(177);
cDelimEle = Char(178);
########################################################################################################################
### Clear Target View
sFilter = '';
sFilter = 'Year Month' | cDelimEleStart | cSAYear | ' ' |cSAMonth;

sPro = '}bedrock.cube.data.clear';
ExecuteProcess(sPro ,
  'pLogOutput',0,
  'pCube',cCubTarget,
  'pView',cViewSource,
  'pFilter',sFilter,
  'pFilterParallel','',
  'pParallelThreads',0,
  'pDimDelim',cDelimDim,
  'pEleStartDelim',cDelimEleStart,
  'pEleDelim',cDelimEle,
  'pCubeLogging',0,
  'pTemp',1,
  'pSandbox','');

### End Clear Data
###########################################################################################################################
# set datasource
DataSourceType='Characterdelimited';
DatasourceNameForServer=sFileFullName;
DatasourceAsciiHeaderRecords = 1; 
nLineCount = 0;
###################################################################################################################
######### End Prolog
> ```
>
> #### Metadata
> ```
> ```
>
> #### Data
> ```
######### Data commences
sVal = vValue;

###########################################################################################
### according the Loop "behavior + Measure", we can get "ZL Mgt Report Item" through the Mapping Cube

###################################################################################################
### Load data to cube "ZL Amazon Payments Data Report"
If( CellisUpdateable(cCubTarget, vYearMonth, vYearMonthIndex, vMeasure) > 0);
  CellPutS(sVal, cCubTarget, vYearMonth, vYearMonthIndex, vMeasure);
Endif;
###################################################################################################################

nLineCount =  nLineCount +1;

###################################################################################################################
######### End Data
> ```
>
> #### Epilog
> ```
###################################################################################################################
######### Epilog commences
### recover transaction log state
#CubeSetLogChanges(cCubTarget, cLog);
Cellputs(sLog,'}CubeProperties', cCubTarget, 'LOGGING');

#####################################################################################
### Err Handling
If(nErr <> 0);
  LogOutput('Error', sErr);
  ProcessQuit;
EndIf;
###################################################################################################################
######### End Epilog
> ```


> ### 示例 3：[example03]
> **功能描述**：[dimension update]
>
> #### Prolog
> ```
################################################################
### DatasourceType:     DataWarehouse
### Datasource:         SQL Server dw 
### Target objectType : Dimension
### Datatarget:        COA Account GL
###############################################################################################################################
### Date        Creation of process     Purpose
### 2022/5/11     neil           将用友的会计科目表导入到COA Account GL维度中
### 数据来源可以是用友，金蝶，sap，oracle 等ERP系统的数据库或者CSV文件
###############################################################################################################################
######### Prolog commences
cTim = TimSt( now(), '\Y\m\d\h\i\s');
cInt = Numbertostring( Int(Rand()*10000) );
cProName = Getprocessname();
cViewSource = '}TI' | cProName | '_' | cInt |'_' | cTim;
cSubSource = cViewSource;
cSysCube = 'Sys Parameter';
cSysType = 'Text';
cOutputFolder = Cellgets(cSysCube, 'Server Export Folder', cSysType);
cErrLogFile = Cellgets(cSysCube, 'Server Log Folder', cSysType);
cOutputFullName = cOutputFolder | cProName |'_data_debug.csv';
cErrorFilename = cErrLogFile  |'TM1ProcessError_' | '*' |  cProName | '.log' ;
nErr= 0;
sErr= '';

cTgrDim = 'COA Account GL';
cTgrDim2 = 'Account BS'; 
cTgrDim3 = 'Account PL';
cTgrDim4 = 'Account GL';
cSAYear = pSAYear;
cSAMonth = pSAMonth;
cSAMonthidx00 = Subst(cSAMonth,2,2);
####################################################################################
### test parameter
sYearDim = 'SA Year';
If(Dimix( sYearDim,cSAYear ) = 0);
  nErr = nErr +1;
  sErr = 'Element "' | pSAYear | '" Not Exists in ' | sYearDim | ' Dimension, Please Check Your Paramenter';
  ProcessBreak;
Endif;

sMonthDim = 'SA Month';
If(Dimix( sMonthDim, cSAMonthidx00 ) = 0);
  nErr = nErr +1;
  sErr = 'Element "' | pSAMonth | '" Not Exists in ' | sMonthDim | ' Dimension, Please Check Your Paramenter';
  ProcessBreak;
Endif;
####################################################################################
###define sql variables
cODBCSource = Cellgets(cSysCube, 'SQL Server ODBC Name', cSysType);
cUser = Cellgets(cSysCube, 'SQL Server Admin', cSysType);
cPsd = Cellgets(cSysCube, 'SQL Server Admin Psd', cSysType);
cDBName = 'UFDATA_002_2021';
cProcedureName = 'dim_account_fullname_gl_update';
cSQLMonth = cSAMonthidx00;
### Open ODBC connection
ODBCOpen(cODBCSource, cUser, cPsd);

################################################################################################
### Define sql statement for odbcoutput function to execute
sSQL = 'exec ['|cDBName|'].[dbo].['|cProcedureName|']';
### 调用 SQL Server 数据库的 "dim_account_fullname_gl_update" 存储过程
LogOutput('info', '本次开始获取数据的月份是： ' | cSAYear | cSQLMonth );
LogOutput('info', '正在从'| cDBName | '调用存储过程:'| cProcedureName |'，获取数据，执行的SQL语句是： ' | sSQL);
### Execute SQL Procedure statement
ODBCOutput(cODBCSource,sSQL );

####################################################################################
DataSourceType='ODBC';
DatasourceNameForServer=cODBCSource;
DatasourceNameForClient=cODBCSource;
DatasourceUserName = cUser;
DatasourcePassword = cPsd;
DatasourceQuery=sSQL;
nLineCount = 0;
###################################################################################################################
######### End Prolog
> ```
>
> #### Metadata
> ```
######### Metadata commences

#####################################################################
### define variable , for insert element
vAccountCode = vccode;
#####################################################################
### according logical judge, and insert element & child
If( vLevel0 @<>'null' & vLevel0 @<>''  & vLevel0 @<>'\r\n');
  DimensionElementInsertdirect(cTgrDim, '', vLevel0, 'N');
  If( vLevel1 @<>'null' & vLevel1 @<>''  & vLevel1 @<>'\r\n');
    DimensionElementInsertdirect(cTgrDim, '', vLevel1, 'N');
    DimensionElementComponentAddDirect(cTgrDim, vLevel1, vLevel0,1);
    If( vLevel2 @<>'null' & vLevel2 @<>''  & vLevel2 @<>'\r\n');
    DimensionElementInsertdirect(cTgrDim, '', vLevel2, 'N');
    DimensionElementComponentAddDirect(cTgrDim, vLevel2, vLevel1,1);
      If( vLevel3 @<>'null' & vLevel3 @<>''  & vLevel3 @<>'\r\n');
        DimensionElementInsertdirect(cTgrDim, '', vLevel3, 'N');
        DimensionElementComponentAddDirect(cTgrDim, vLevel3, vLevel2,1);
        If( vLevel4 @<>'null' & vLevel4 @<>''  & vLevel4 @<>'\r\n');
          DimensionElementInsertdirect(cTgrDim, '', vLevel4, 'N');
          DimensionElementComponentAddDirect(cTgrDim, vLevel4, vLevel3,1);
        Endif;
      Endif;
    Endif;
  Endif;
Endif;
cEle = 'All GL Accounts';
If(DType(cTgrDim, vAccountCode) @= 'N');
If(ElIsPar(cTgrDim, cEle, vAccountCode)=0);
  DimensionElementComponentAddDirect(cTgrDim, cEle, vAccountCode,1);
Endif;
Endif;

#####################################################################
### End Metadata

> ```
>
> #### Data
> ```
######### Data commences

#################################################################################################
### 添加 COA Account GL 维度的attribute
vAccountCode = vccode;
vAccountName = vccodename;
vEle = vAccountCode;
sTgrDim = cTgrDim;
vAttrName = '中文';
AttrPutS(vAccountName, sTgrDim, vEle, vAttrName, '', 1);
################################################################################################################
####### end data
> ```
>
> #### Epilog
> ```
######### Epilog commences

### close ODBC connection 
ODBCClose(cODBCSource);
#####################################################################################
### Err Handling
If(nErr <> 0);
  LogOutput('Error', sErr);
  ProcessQuit;
EndIf;
#####################################################################################
### End Epilog

> ```