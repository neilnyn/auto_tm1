"""One-time generator for APQ Logging dimension spec JSON files."""
import json
from datetime import date, timedelta
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent


def write_spec(filename, dimension_name, elements, edges,
               attributes=None, attribute_values=None, subsets=None):
    spec = {
        "_spec_to_mcp_mapping": {
            "_comment": "Each top-level field maps to specific MCP tool calls.",
            "execution_order": [
                "1. dimension_name + elements + edges + hierarchy -> create_dimension()",
                "2. attributes[] -> create_element_attribute() for each attribute",
                "3. attribute_values[] -> write_element_attributes() (batch)",
                "4. subsets[] -> create_subset() for each"
            ]
        },
        "dimension_name": dimension_name,
        "hierarchy_name": None,
        "elements": elements,
        "edges": edges,
        "add_edges": [],
        "remove_edges": [],
        "attributes": attributes or [],
        "attribute_values": attribute_values or [],
        "subsets": subsets or []
    }
    path = OUTPUT_DIR / filename
    path.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Written: {path.name} ({len(elements)} elements, {len(edges)} edges)")


def main():
    print("Generating APQ Logging dimension specs...")

    # --- 1. }APQ Parallelization Control Measure (2 elements, 1 edge) ---
    write_spec(
        "}APQ_Parallelization_Control_Measure_dimension-spec.json",
        "}APQ Parallelization Control Measure",
        elements=[
            {"name": "Disabled", "type": "Numeric"},
            {"name": "Total }APQ Parallelization Control Measure", "type": "Consolidated"},
        ],
        edges=[
            {"parent": "Total }APQ Parallelization Control Measure", "child": "Disabled", "weight": 1.0},
        ],
    )

    # --- 2. }APQ Cube Last Updated Measure (4 elements, 3 edges) ---
    write_spec(
        "}APQ_Cube_Last_Updated_Measure_dimension-spec.json",
        "}APQ Cube Last Updated Measure",
        elements=[
            {"name": "nLastTimeUpdate", "type": "Numeric"},
            {"name": "sProcess", "type": "String"},
            {"name": "sProcessRunBy", "type": "String"},
            {"name": "Total }APQ Cube Last Updated Measure", "type": "Consolidated"},
        ],
        edges=[
            {"parent": "Total }APQ Cube Last Updated Measure", "child": "nLastTimeUpdate", "weight": 1.0},
            {"parent": "Total }APQ Cube Last Updated Measure", "child": "sProcess", "weight": 1.0},
            {"parent": "Total }APQ Cube Last Updated Measure", "child": "sProcessRunBy", "weight": 1.0},
        ],
    )

    # --- 3. }APQ Processes (1 element, 0 edges) ---
    write_spec(
        "}APQ_Processes_dimension-spec.json",
        "}APQ Processes",
        elements=[
            {"name": "Total APQ Processes", "type": "Consolidated"},
        ],
        edges=[],
    )

    # --- 4. }APQ Cubes (1 element, 0 edges) ---
    write_spec(
        "}APQ_Cubes_dimension-spec.json",
        "}APQ Cubes",
        elements=[
            {"name": "Total }APQ Cubes", "type": "Consolidated"},
        ],
        edges=[],
    )

    # --- 5. }APQ Process Execution Log Measure (16 elements, 15 edges) ---
    measure_n = [
        "nProcessStartTime", "nProcessStartedFlag", "nProcessExecutionIndex",
        "nProcessExecutionIntraDayIndex", "nProcessFinishTime",
        "nProcessCompletedFlag", "nMetaDataRecordCount", "nDataRecordCount",
        "nPrologMinorErrorCount", "nMetaDataMinorErrorCount",
        "nDataMinorErrorCount", "nProcessReturnCode",
    ]
    measure_s = ["sRunBy", "sParams", "sProcessErrorLogFile"]
    measure_c = "Total }APQ Process Execution Log Measure"

    measure_elements = (
        [{"name": n, "type": "Numeric"} for n in measure_n]
        + [{"name": s, "type": "String"} for s in measure_s]
        + [{"name": measure_c, "type": "Consolidated"}]
    )
    measure_edges = [
        {"parent": measure_c, "child": n, "weight": 1.0} for n in (measure_n + measure_s)
    ]

    write_spec(
        "}APQ_Process_Execution_Log_Measure_dimension-spec.json",
        "}APQ Process Execution Log Measure",
        elements=measure_elements,
        edges=measure_edges,
    )

    # --- 6. }APQ Time Day (367 elements, 365 edges) ---
    days_2026 = []
    start = date(2026, 1, 1)
    for i in range(365):  # 2026 is not a leap year
        d = start + timedelta(days=i)
        days_2026.append(d.strftime("%m-%d"))

    day_elements = [
        {"name": "Total Year", "type": "Consolidated"},
        {"name": "D000", "type": "Consolidated"},
    ] + [{"name": d, "type": "Numeric"} for d in days_2026]

    day_edges = [
        {"parent": "Total Year", "child": d, "weight": 1.0} for d in days_2026
    ]

    write_spec(
        "}APQ_Time_Day_dimension-spec.json",
        "}APQ Time Day",
        elements=day_elements,
        edges=day_edges,
    )

    # --- 7. }APQ Time Minute (1442 elements, 2880 edges) ---
    minutes = [f"{h:02d}:{m:02d}" for h in range(24) for m in range(60)]

    minute_elements = [
        {"name": "Total Day", "type": "Consolidated"},
        {"name": "Total Day Entry", "type": "Consolidated"},
    ] + [{"name": m, "type": "Numeric"} for m in minutes]

    minute_edges = [
        {"parent": "Total Day", "child": m, "weight": 1.0} for m in minutes
    ] + [
        {"parent": "Total Day Entry", "child": m, "weight": 1.0} for m in minutes
    ]

    write_spec(
        "}APQ_Time_Minute_dimension-spec.json",
        "}APQ Time Minute",
        elements=minute_elements,
        edges=minute_edges,
    )

    print("Done. All 7 dimension specs generated.")


if __name__ == "__main__":
    main()
