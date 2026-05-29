---
name: apq-logging-infrastructure
description: Full APQ logging infrastructure on Neil instance -- cubes, dimensions, processes, and Process Run Log
metadata:
  type: reference
---

# APQ Logging Infrastructure on Neil Instance

## Main Cube: `APQ TM1 Log Recorder`
Dimension order (critical for CellPutS/CellPutN):
1. `}APQ Time Year`
2. `}APQ Time Day in Year`
3. `}APQ Time Minute`
4. `}APQ Time Second`
5. `TM1 Logger` (28 elements: 27 N-leaf + 1 C "All TM1 Loggers")
6. `TM1 Log Level` (6 S-elements: INFO, WARN, ERROR, FATAL, DEBUG, UNKNOWN)
7. `Line Item Log` (126,344 elements: 126,343 N-leaf numbered items + 1 C "All Line Items")
8. `TM1 Log Type` (3 S-elements: TM1 Server log, TM1 Event log, TM1 Transaction log)
9. `}APQ TM1 Log Recorder Measure` (3 elements: Execution Log [S], No Empty Flag [N], Execution Log Simple [S])

Rules: `Feedstrings; Skipcheck;` with empty feeders. No substantive rules.

Data source: Parses `tm1server.log` via ASCII datasource. Process copies the log file first, then parses each line extracting year, month-day, time (HH:MM), seconds, log level, and logger from the fixed-width format.

## Supporting Process: `}Process Run Log`
Cube: `}Process Run Log`
Dimension order:
1. `Process Run ID` (105,846 elements: 105,845 N-leaf + 1 C "All RunIDs") -- attribute: "Used Flag"
2. `Line Item` (default `0000`)
3. `}Processes`
4. `Data Source Process Run Log` (4 elements: 3 N-leaf [Chore, Manually, TM1 Rest API] + 1 C "All DataSources")
5. `}Process Run Log Measure`

Rules: Derives "Process Execution Parameters Simplify" from "Process Execution Parameters" by extracting content after "parameters" keyword.

## Key TI Processes

### `Sys.APQ TM1 Log Recorder.Design`
- Datasource: ASCII (reads tm1server.log copy)
- Parameters: `pImportRowCount` (Numeric, default 999999), `pTM1LogType` (String, default "TM1 Server log")
- Variables: `vString` (String, position 1)
- Prolog: Creates all APQ dimensions and cube if they don't exist; copies tm1server.log to a backup file for parsing
- Data: Parses each line of the log file, extracts timestamp/log-level/logger, writes to cube via CellPutS (writes to consolidated rollup elements as well for fast querying)
- Epilog: Cleans up temp files, constructs stargate view "01.Check Data Load"
- Author: Niko XUE, 2022/7/19

### `69.Sys Run Process Log`
- Datasource: None
- Parameters: `pRunProName` (String), `pRunFlag` (Numeric: 0=Start, 1=End), `pRunParams` (String), `pUIDTemp` (String, default timestamp-based ID)
- Called by other processes at start (pRunFlag=0) and end (pRunFlag=1) to log execution status, start/finish times, duration, and who ran it
- Writes to `}Process Run Log` cube
- Author: Niko XUE, 2022/7/18

### Usage Pattern
Most processes call `69.Sys Run Process Log` via a pattern in their Prolog:
```
cTM1RunProcessLog = CellgetS('Sys Parameter', 'TM1 Run Log Pro', 'Text');
ExecuteProcess(cTM1RunProcessLog,'pRunProName',cThisProName,'pRunFlag',0,'pRunParams',cLogInfo);
```
And in their Epilog:
```
ExecuteProcess(cTM1RunProcessLog,'pRunProName',cThisProName,'pRunFlag',1,'pRunParams',cLogInfo);
```

## Views on `APQ TM1 Log Recorder`
- `01.Check Data Load` -- Public, user-facing view with Year/Logger/LogType/LogLevel as titles, Day/Minute/Second as rows, Measure as column. Defaults: Year=2023, Logger=TM1.Process, LogType=TM1 Server log, LogLevel=INFO
- `}Pro_Import_APQ TM1 Log Recorder` -- System import view, all consolidations selected
- `locking test` -- Public view (test artifact)

## APQ Control Dimensions (all `}` prefix)
- `}APQ Time Year` -- years (e.g., 2022, 2023) with "Total Years" consolidation
- `}APQ Time Day in Year` -- day-in-year entries (e.g., "07-16") with "Total Year" consolidation and quarterly/monthly/relative time rollups
- `}APQ Time Minute` -- minute-level time (e.g., "07-16" HH:MM) with "Total Day" consolidation and time-period rollups
- `}APQ Time Second` -- second-level entries (00-59) with "Total Minute" consolidation
- `}APQ TM1 Log Recorder Measure` -- 3 elements (Execution Log [S], No Empty Flag [N], Execution Log Simple [S])

## TM1 Logger Leaf Elements (27)
Event, Event.Thread, TM1.Application, TM1.Blob, TM1.Chore, TM1.Comm, TM1.Cube, TM1.Cube.Dependency, TM1.Dimension, TM1.Event, TM1.HttpRequest, TM1.HttpRequestBody, TM1.HttpResponse, TM1.HttpResponseBody, TM1.Lock.Exception, TM1.Lock.SYSMT, TM1.Login, TM1.Mdx.Interface, TM1.MetaLogger, TM1.NGAPI.REST, TM1.Process, TM1.Rule, TM1.SQLAPI, TM1.Server, TM1.Subset, TM1.TILogOutput, TM1.Transaction

## Note
The `get_dimension_info` and `get_dimension_info` tools error on dimensions starting with `}` due to a format string parsing issue ("Single '}' encountered in format string"). Use `get_leaf_elements` or the process code as alternative sources of truth for these control dimensions.
