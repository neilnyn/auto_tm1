"""TM1 Connector — all TM1 interaction logic.

All TM1 read/write operations are encapsulated in the TM1Manager class.
The MCP tool layer (tm1_mcp_tool.py) only calls through this class.
"""

from configparser import ConfigParser
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any

from loguru import logger
from TM1py.Exceptions import TM1pyException
from mdxpy import MdxBuilder, MdxHierarchySet
from TM1py.Objects import Dimension, Element, ElementAttribute, Hierarchy, Process, Axis
from TM1py.Services import TM1Service

import json

_TYPE_ABBREV = {"Consolidated": "C", "Numeric": "N", "String": "S"}

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_spec_path(file_path: str) -> Path:
    """Resolve a spec file path relative to project root and validate it."""
    p = Path(file_path)
    if not p.is_absolute():
        p = _PROJECT_ROOT / p
    if not p.exists():
        raise TM1OperationError(f"Spec file not found: {p}")
    if p.suffix.lower() != ".json":
        raise TM1OperationError(f"Expected .json file, got: {p}")
    return p


def _children_map(parents_map: dict[str, list[str]]) -> dict[str, list[str]]:
    """Build parent→children dict from child→parents dict."""
    cm: dict[str, list[str]] = {}
    for child, parents in parents_map.items():
        for parent in parents:
            cm.setdefault(parent, []).append(child)
    return cm


class TM1OperationError(RuntimeError):
    """Raised when a TM1 server operation fails."""


def _tm1_api(operation: str):
    """Decorator that converts TM1pyException to TM1OperationError."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except TM1pyException as exc:
                raise TM1OperationError(f"{operation}: {exc}") from exc
        return wrapper
    return decorator


class TM1Manager:
    """Manages connections to TM1 instances.

    Usage patterns:
        with TM1Manager.call("FDI") as tm1:
            cubes = tm1.list_cubes()

        async with TM1Manager("FDI") as tm1:
            cubes = tm1.list_cubes()

        tm1 = TM1Manager("FDI").connect()
        cubes = tm1.list_cubes()
        tm1.disconnect()
    """

    _configs: dict[str, dict] | None = None
    _configs_path: Path | None = None

    def __init__(
        self,
        instance_name: str,
        config_path: str | Path = "config/tm1py_config.ini",
    ):
        self._instance_name = instance_name
        self._config_path = Path(config_path)
        self._tm1: TM1Service | None = None

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_config_path(relative_path: Path) -> Path:
        candidates: list[Path] = []
        if relative_path.is_absolute():
            candidates.append(relative_path)
        candidates.extend([
            relative_path.resolve(),
            Path.cwd() / relative_path,
            Path(__file__).resolve().parent.parent / relative_path,
        ])
        for candidate in candidates:
            if candidate.exists():
                return candidate
        searched = "\n  ".join(str(c) for c in candidates)
        raise FileNotFoundError(
            f"Config file not found. Searched:\n  {searched}"
        )

    @classmethod
    def _load_configs(cls, config_path: Path) -> dict[str, dict]:
        if cls._configs is not None and cls._configs_path == config_path:
            return cls._configs

        config = ConfigParser()
        resolved = cls._resolve_config_path(config_path)
        config.read(resolved, encoding="utf-8")
        if not config.sections():
            raise ValueError(f"No TM1 instances found in config: {resolved}")

        cls._configs = {}
        for section in config.sections():
            params = dict(config.items(section))
            if "port" in params:
                params["port"] = int(params["port"])
            if "ssl" in params:
                params["ssl"] = params["ssl"].lower() == "true"
            if "decode_b64" in params:
                params["decode_b64"] = params["decode_b64"].lower() == "true"
            cls._configs[section] = params

        cls._configs_path = resolved
        logger.debug(f"Loaded {len(cls._configs)} TM1 instances from {resolved}")
        return cls._configs

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> "TM1Manager":
        configs = self._load_configs(self._config_path)
        if self._instance_name not in configs:
            raise KeyError(
                f"Instance '{self._instance_name}' not found. "
                f"Available: {', '.join(configs.keys())}"
            )
        cfg = configs[self._instance_name].copy()
        self._tm1 = TM1Service(**cfg)
        logger.info(f"Connected to TM1: {self._instance_name}")
        return self

    def disconnect(self) -> None:
        if self._tm1 is None:
            return
        try:
            self._tm1.logout()
            logger.info(f"Disconnected from TM1: {self._instance_name}")
        except Exception as exc:
            logger.warning(f"Error during disconnect: {exc}")
        finally:
            self._tm1 = None

    async def __aenter__(self) -> "TM1Manager":
        return self.connect()

    async def __aexit__(self, *args: Any) -> None:
        self.disconnect()

    @classmethod
    @contextmanager
    def call(
        cls,
        instance_name: str,
        config_path: str | Path = "config/tm1py_config.ini",
    ):
        """Synchronous context manager for one-shot tool calls."""
        mgr = cls(instance_name, config_path)
        try:
            mgr.connect()
            yield mgr
        finally:
            mgr.disconnect()

    @property
    def service(self) -> TM1Service:
        if self._tm1 is None:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._tm1

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @classmethod
    def list_instances(
        cls, config_path: str | Path = "config/tm1py_config.ini"
    ) -> list[str]:
        configs = cls._load_configs(Path(config_path))
        return sorted(configs.keys())

    @staticmethod
    def get_process_template() -> dict[str, Any]:
        return {
            "name": "",
            "datasource_type": "None",
            "has_security_access": False,
            "parameters": [],
            "variables": [],
            "prolog_procedure": "",
            "metadata_procedure": "",
            "data_procedure": "",
            "epilog_procedure": "",
        }

    @staticmethod
    def _validate_csv_path(file_path: str) -> Path:
        p = Path(file_path).resolve()
        if p.suffix.lower() != ".csv":
            raise ValueError(f"Only CSV files are allowed, got: {p.suffix}")
        if ".." in p.parts:
            raise ValueError(f"Path traversal not allowed: {file_path}")
        if not p.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return p

    # ------------------------------------------------------------------
    # Dimension — read-only
    # ------------------------------------------------------------------

    def _resolve_hierarchy(
        self, dimension_name: str, hierarchy_name: str | None = None
    ) -> str:
        if hierarchy_name:
            return hierarchy_name
        return self.service.dimensions.hierarchies.get_all_names(dimension_name)[0]

    @_tm1_api("list dimensions")
    def list_dimensions(self, skip_control_dims: bool = True) -> list[str]:
        names = self.service.dimensions.get_all_names(
            skip_control_dims=skip_control_dims
        )
        return sorted(names)

    @_tm1_api("get dimension info")
    def get_dimension_info(
        self,
        dimension_name: str,
        hierarchy_name: str | None = None,
    ) -> dict[str, Any]:
        """Get dimension overview: element counts, level count, attribute names, and root elements."""
        hier = self._resolve_hierarchy(dimension_name, hierarchy_name)
        types = self.service.elements.get_element_types(dimension_name, hier)

        n_count = sum(1 for t in types.values() if t == "Numeric")
        s_count = sum(1 for t in types.values() if t == "String")
        c_count = sum(1 for t in types.values() if t == "Consolidated")

        all_attrs = self.service.elements.get_element_attributes(
            dimension_name, hier
        )
        alias_names = sorted(a.name for a in all_attrs if a.attribute_type == "Alias")
        attr_names = sorted(a.name for a in all_attrs if a.attribute_type != "Alias")
        parents_map = self.service.elements.get_parents_of_all_elements(
            dimension_name, hier
        )
        all_elems = set(types.keys())
        has_parent = set([_ for _ in parents_map if parents_map.get(_) != []])
        roots_list = sorted(all_elems - has_parent)
        root_elements = [
            {"name": r, "type": _TYPE_ABBREV.get(types.get(r, "Numeric"), "N")}
            for r in roots_list
        ]

        cm = _children_map(parents_map)
        max_level = 0
        queue: list[tuple[str, int]] = [(r, 0) for r in roots_list]
        while queue:
            elem, lvl = queue.pop(0)
            if lvl > max_level:
                max_level = lvl
            for ch in cm.get(elem, []):
                queue.append((ch, lvl + 1))

        return {
            "dimension": dimension_name,
            "hierarchy": hier,
            "element_counts": {
                "numeric": n_count,
                "string": s_count,
                "consolidated": c_count,
                "total": n_count + s_count + c_count,
            },
            "level_count": max_level + 1,
            "alias_names": alias_names,
            "attribute_names": attr_names,
            "root_elements": root_elements,
        }

    @_tm1_api("get leaf elements")
    def get_leaf_elements(
        self,
        dimension_name: str,
        hierarchy_name: str | None = None,
        under: str | None = None,
        search: str | None = None,
        sample: int | None = None,
    ) -> dict[str, Any]:
        """Get leaf (N/S) elements. Use 'under' to scope to a parent, 'search' to filter by name, 'sample' to limit results."""
        hier = self._resolve_hierarchy(dimension_name, hierarchy_name)

        if under:
            leaf_names = self.service.dimensions.hierarchies.elements.get_members_under_consolidation(
                dimension_name, hier, under, leaves_only=True
            )
            elements = sorted(leaf_names)
        else:
            elements = sorted(
                self.service.elements.get_leaf_element_names(dimension_name, hier)
            )

        if search:
            kw = search.lower()
            elements = [e for e in elements if kw in e.lower()]

        total = len(elements)
        truncated = sample is not None and sample < total
        if truncated:
            elements = elements[:sample]

        return {
            "dimension": dimension_name,
            "hierarchy": hier,
            "under": under,
            "leaf_elements": elements,
            "total": total,
            "truncated": truncated,
        }

    @_tm1_api("expand element")
    def expand_element(
        self,
        dimension_name: str,
        element_name: str,
        hierarchy_name: str | None = None,
        depth: int | None = 1,
        include_attributes: bool = False,
    ) -> dict[str, Any]:
        """Expand an element to see its children/subtree. depth=1 for immediate children, depth=None for full subtree."""
        hier = self._resolve_hierarchy(dimension_name, hierarchy_name)
        types = self.service.elements.get_element_types(dimension_name, hier)
        parents_map = self.service.elements.get_parents_of_all_elements(
            dimension_name, hier
        )
        cm = _children_map(parents_map)

        if element_name not in types:
            raise ValueError(
                f"Element '{element_name}' not found in '{dimension_name}'"
            )

        def _build_node(elem: str, current_depth: int) -> dict[str, Any]:
            node: dict[str, Any] = {
                "name": elem,
                "type": _TYPE_ABBREV.get(types.get(elem, "Numeric"), "N"),
            }
            if types.get(elem) == "Consolidated" and (
                depth is None or current_depth < depth
            ):
                children = cm.get(elem, [])
                if children:
                    node["children"] = sorted(
                        (_build_node(c, current_depth + 1) for c in children),
                        key=lambda n: n["name"],
                    )
            return node

        tree = _build_node(element_name, 0)

        result: dict[str, Any] = {
            "dimension": dimension_name,
            "hierarchy": hier,
            "depth_limit": depth,
        }
        result.update(tree)

        if include_attributes:
            attr_names = self.service.elements.get_alias_element_attributes(
                dimension_name, hier
            )
            if attr_names:
                attrs: dict[str, Any] = {}
                for attr in attr_names:
                    vals = self.service.elements.get_attribute_of_elements(
                        dimension_name, hier, attr, elements=[element_name]
                    )
                    if vals:
                        attrs[attr] = vals
                if attrs:
                    result["attributes"] = attrs

        return result

    @_tm1_api("get parents")
    def get_parents(
        self,
        dimension_name: str,
        elements: list[str],
        hierarchy_name: str | None = None,
    ) -> dict[str, Any]:
        """Get all parent elements for one or more elements."""
        hier = self._resolve_hierarchy(dimension_name, hierarchy_name)
        parents_map = self.service.elements.get_parents_of_all_elements(
            dimension_name, hier
        )
        result: dict[str, Any] = {}
        for elem in elements:
            if elem in parents_map:
                result[elem] = parents_map[elem]
            else:
                result[elem] = []
        return {
            "dimension": dimension_name,
            "hierarchy": hier,
            "parents": result,
        }

    @_tm1_api("get element attributes")
    def get_element_attributes(
        self,
        dimension_name: str,
        hierarchy_name: str | None = None,
        elements: list[str] | None = None,
        attribute_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get element attribute values. Filter by elements and/or attribute names."""
        hier = self._resolve_hierarchy(dimension_name, hierarchy_name)
        all_attr_names = self.service.elements.get_alias_element_attributes(
            dimension_name, hier
        )
        target_attrs = attribute_names or all_attr_names
        target_elems = elements or list(
            self.service.elements.get_element_names(dimension_name, hier)
        )
        if not target_attrs or not target_elems:
            return {
                "dimension": dimension_name,
                "hierarchy": hier,
                "attributes": {},
            }

        attrs: dict[str, dict[str, Any]] = {}
        for attr in target_attrs:
            vals = self.service.elements.get_attribute_of_elements(
                dimension_name, hier, attr, elements=target_elems
            )
            for elem, val in vals.items():
                attrs.setdefault(elem, {})[attr] = val

        return {
            "dimension": dimension_name,
            "hierarchy": hier,
            "attributes": attrs,
        }

    # ------------------------------------------------------------------
    # Dimension — write
    # ------------------------------------------------------------------

    @_tm1_api("create dimension")
    def create_dimension(
        self,
        dimension_name: str,
        elements: list[dict[str, Any]],
        edges: list[dict[str, Any]] | None = None,
        hierarchy_name: str | None = None,
    ) -> dict[str, Any]:
        """Create a dimension with elements and hierarchy.

        elements: [{"name": "Total", "type": "Consolidated"}, ...]
        edges: [{"parent": "Total", "child": "Item1", "weight": 1.0}, ...]
        """
        hier = hierarchy_name or dimension_name
        tm1_elements = [
            Element(name=e["name"], element_type=e["type"])
            for e in elements
        ]
        tm1_edges: dict[tuple[str, str], int | float] = {}
        for edge in (edges or []):
            tm1_edges[(edge["parent"], edge["child"])] = edge.get("weight", 1.0)
        hierarchy = Hierarchy(
            name=hier,
            dimension_name=dimension_name,
            elements=tm1_elements,
            edges=tm1_edges if tm1_edges else None,
        )
        dimension = Dimension(name=dimension_name, hierarchies=[hierarchy])
        self.service.dimensions.create(dimension)
        logger.info(f"Created dimension '{dimension_name}' with {len(elements)} elements")
        return {
            "success": True,
            "dimension_name": dimension_name,
            "element_count": len(elements),
        }

    @_tm1_api("delete dimension")
    def delete_dimension(self, dimension_name: str) -> dict[str, Any]:
        self.service.dimensions.delete(dimension_name)
        logger.info(f"Deleted dimension '{dimension_name}'")
        return {"success": True, "dimension_name": dimension_name}

    @_tm1_api("add elements")
    def add_elements(
        self,
        dimension_name: str,
        elements: list[dict[str, Any]],
        hierarchy_name: str | None = None,
    ) -> dict[str, Any]:
        """Add elements to an existing dimension.

        elements: [{"name": "NewElem", "type": "Numeric"}, ...]
        """
        hier = self._resolve_hierarchy(dimension_name, hierarchy_name)
        tm1_elements = [
            Element(name=e["name"], element_type=e["type"])
            for e in elements
        ]
        self.service.dimensions.hierarchies.elements.add_elements(
            dimension_name, hier, tm1_elements
        )
        logger.info(f"Added {len(elements)} elements to '{dimension_name}'")
        return {
            "success": True,
            "dimension_name": dimension_name,
            "added_count": len(elements),
        }

    @_tm1_api("delete elements")
    def delete_elements(
        self,
        dimension_name: str,
        element_names: list[str],
        hierarchy_name: str | None = None,
    ) -> dict[str, Any]:
        hier = self._resolve_hierarchy(dimension_name, hierarchy_name)
        try:
            self.service.dimensions.hierarchies.elements.delete_elements(
                dimension_name, hier, element_names
            )
        except (TM1pyException, AttributeError):
            for name in element_names:
                self.service.dimensions.hierarchies.elements.delete(
                    dimension_name, hier, name
                )
        logger.info(f"Deleted {len(element_names)} elements from '{dimension_name}'")
        return {
            "success": True,
            "dimension_name": dimension_name,
            "deleted_count": len(element_names),
        }

    @_tm1_api("update hierarchy")
    def update_hierarchy(
        self,
        dimension_name: str,
        add_edges: list[dict[str, Any]] | None = None,
        remove_edges: list[dict[str, Any]] | None = None,
        hierarchy_name: str | None = None,
    ) -> dict[str, Any]:
        """Add/remove consolidation edges.

        add_edges: [{"parent": "Total", "child": "Item1", "weight": 1.0}, ...]
        remove_edges: [{"parent": "Total", "child": "Item1"}, ...]
        """
        hier = self._resolve_hierarchy(dimension_name, hierarchy_name)
        added = 0
        removed = 0
        if add_edges:
            edges: dict[tuple[str, str], int | float] = {}
            for edge in add_edges:
                edges[(edge["parent"], edge["child"])] = edge.get("weight", 1.0)
            self.service.dimensions.hierarchies.elements.add_edges(
                dimension_name, hier, edges=edges
            )
            added = len(add_edges)
        if remove_edges:
            edge_tuples = [(e["parent"], e["child"]) for e in remove_edges]
            try:
                self.service.dimensions.hierarchies.elements.delete_edges(
                    dimension_name, hier, edges=edge_tuples
                )
            except (TM1pyException, AttributeError):
                for parent, child in edge_tuples:
                    self.service.dimensions.hierarchies.elements.remove_edge(
                        dimension_name, hier, parent, child
                    )
            removed = len(remove_edges)
        logger.info(
            f"Updated hierarchy for '{dimension_name}': "
            f"added {added} edges, removed {removed} edges"
        )
        return {
            "success": True,
            "dimension_name": dimension_name,
            "edges_added": added,
            "edges_removed": removed,
        }

    @_tm1_api("create element attribute")
    def create_element_attribute(
        self,
        dimension_name: str,
        attribute_name: str,
        attribute_type: str = "String",
        hierarchy_name: str | None = None,
    ) -> dict[str, Any]:
        """Create a new element attribute column on a dimension."""
        hier = self._resolve_hierarchy(dimension_name, hierarchy_name)
        attr = ElementAttribute(name=attribute_name, attribute_type=attribute_type)
        self.service.dimensions.hierarchies.elements.create_element_attribute(
            dimension_name, hier, attr
        )
        logger.info(f"Created attribute '{attribute_name}' on '{dimension_name}'")
        return {
            "success": True,
            "dimension_name": dimension_name,
            "attribute_name": attribute_name,
            "attribute_type": attribute_type,
        }

    @_tm1_api("write element attributes")
    def write_element_attributes(
        self,
        dimension_name: str,
        attribute_values: list[dict[str, Any]],
        hierarchy_name: str | None = None,
    ) -> dict[str, Any]:
        """Write attribute values for elements via the }ElementAttributes cube.

        attribute_values: [{"element": "Q1", "attribute": "Alias", "value": "Quarter 1"}, ...]
        """
        attr_cube = f"}}ElementAttributes_{dimension_name}"
        cellset: dict[tuple[str, str], Any] = {}
        for entry in attribute_values:
            cellset[(entry["element"], entry["attribute"])] = entry["value"]
        self.service.cells.write_values(attr_cube, cellset)
        logger.info(
            f"Wrote {len(attribute_values)} attribute values on '{dimension_name}'"
        )
        return {
            "success": True,
            "dimension_name": dimension_name,
            "values_updated": len(attribute_values),
        }

    # ------------------------------------------------------------------
    # Dimension — file-based write (for large specs)
    # ------------------------------------------------------------------

    @_tm1_api("create dimension from file")
    def create_dimension_from_file(self, file_path: str) -> dict[str, Any]:
        """Create a full dimension from a spec JSON file.

        The spec follows the dimension-spec.json format with keys:
        dimension_name, hierarchy_name, elements, edges, attributes,
        attribute_values, subsets.
        """
        p = _resolve_spec_path(file_path)
        spec = json.loads(p.read_text(encoding="utf-8"))
        dim_name = spec["dimension_name"]
        hier_name = spec.get("hierarchy_name")

        self.create_dimension(
            dimension_name=dim_name,
            elements=spec["elements"],
            edges=spec.get("edges"),
            hierarchy_name=hier_name,
        )
        attrs_created = 0
        for attr in spec.get("attributes", []):
            self.create_element_attribute(
                dimension_name=dim_name,
                attribute_name=attr["name"],
                attribute_type=attr.get("type", "String"),
                hierarchy_name=hier_name,
            )
            attrs_created += 1

        values_written = 0
        if spec.get("attribute_values"):
            self.write_element_attributes(
                dimension_name=dim_name,
                attribute_values=spec["attribute_values"],
                hierarchy_name=hier_name,
            )
            values_written = len(spec["attribute_values"])

        subsets_created = 0
        for sub in spec.get("subsets", []):
            self.create_subset(
                dimension_name=dim_name,
                subset_name=sub["name"],
                hierarchy_name=hier_name,
                elements=sub.get("elements"),
                expression=sub.get("expression"),
            )
            subsets_created += 1

        logger.info(f"Created dimension '{dim_name}' from spec file (full build)")
        return {
            "success": True,
            "dimension_name": dim_name,
            "element_count": len(spec["elements"]),
            "attributes_created": attrs_created,
            "attribute_values_written": values_written,
            "subsets_created": subsets_created,
        }

    @_tm1_api("add elements from file")
    def add_elements_from_file(
        self,
        file_path: str,
        dimension_name: str,
        hierarchy_name: str | None = None,
    ) -> dict[str, Any]:
        """Add elements to an existing dimension from a JSON file.

        Accepts a plain array [{"name":..., "type":...}] or
        {"elements": [{"name":..., "type":...}]}.
        """
        p = _resolve_spec_path(file_path)
        data = json.loads(p.read_text(encoding="utf-8"))
        elements = data if isinstance(data, list) else data["elements"]
        return self.add_elements(dimension_name, elements=elements, hierarchy_name=hierarchy_name)

    @_tm1_api("update hierarchy from file")
    def update_hierarchy_from_file(
        self,
        file_path: str,
        dimension_name: str,
        hierarchy_name: str | None = None,
    ) -> dict[str, Any]:
        """Add/remove edges from a JSON file.

        File format: {"add_edges": [...], "remove_edges": [...]}.
        """
        p = _resolve_spec_path(file_path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return self.update_hierarchy(
            dimension_name,
            add_edges=data.get("add_edges"),
            remove_edges=data.get("remove_edges"),
            hierarchy_name=hierarchy_name,
        )

    @_tm1_api("write element attributes from file")
    def write_element_attributes_from_file(
        self,
        file_path: str,
        dimension_name: str,
        hierarchy_name: str | None = None,
    ) -> dict[str, Any]:
        """Write attribute values from a JSON file.

        Accepts a plain array [{"element":..., "attribute":..., "value":...}] or
        {"attribute_values": [{"element":..., "attribute":..., "value":...}]}.
        """
        p = _resolve_spec_path(file_path)
        data = json.loads(p.read_text(encoding="utf-8"))
        values = data if isinstance(data, list) else data["attribute_values"]
        return self.write_element_attributes(
            dimension_name, attribute_values=values, hierarchy_name=hierarchy_name,
        )

    # ------------------------------------------------------------------
    # Cube — read-only
    # ------------------------------------------------------------------

    @_tm1_api("list cubes")
    def list_cubes(self, skip_control_cubes: bool = True) -> list[str]:
        names = self.service.cubes.get_all_names(
            skip_control_cubes=skip_control_cubes
        )
        return sorted(names)

    @_tm1_api("get cube")
    def get_cube(self, cube_name: str) -> dict[str, Any]:
        dims = self.service.cubes.get_dimension_names(cube_name)
        last_update = ""
        try:
            last_update = self.service.cubes.get_last_data_update(cube_name)
        except TM1pyException:
            pass
        result: dict[str, Any] = {
            "name": cube_name,
            "dimensions": dims,
            "last_data_update": last_update,
        }
        try:
            rules_errors = self.service.cubes.check_rules(cube_name)
            result["rules_errors"] = rules_errors
        except TM1pyException:
            result["rules_errors"] = None
        return result

    @_tm1_api("find cubes by dimension")
    def find_cubes_using_dimension(
        self, dimension_name: str, skip_control_cubes: bool = True
    ) -> list[str]:
        return self.service.cubes.search_for_dimension(
            dimension_name, skip_control_cubes=skip_control_cubes
        )

    @_tm1_api("get cube rules")
    def get_cube_rules(self, cube_name: str) -> str:
        """Return the full rules text of a cube. Returns empty string if no rules."""
        cube = self.service.cubes.get(cube_name)
        if cube.has_rules:
            return str(cube.rules)
        return ""

    # ------------------------------------------------------------------
    # Cube — write
    # ------------------------------------------------------------------

    @_tm1_api("create cube")
    def create_cube(self, cube_name: str, dimensions: list[str]) -> dict[str, Any]:
        from TM1py.Objects import Cube
        cube = Cube(name=cube_name, dimensions=dimensions)
        self.service.cubes.create(cube)
        logger.info(f"Created cube '{cube_name}' with dims {dimensions}")
        return {"success": True, "cube_name": cube_name, "dimensions": dimensions}

    @_tm1_api("delete cube")
    def delete_cube(self, cube_name: str) -> dict[str, Any]:
        self.service.cubes.delete(cube_name)
        logger.info(f"Deleted cube '{cube_name}'")
        return {"success": True, "cube_name": cube_name}

    # ------------------------------------------------------------------
    # View — read-only
    # ------------------------------------------------------------------

    @_tm1_api("list views")
    def list_views(self, cube_name: str) -> dict[str, list[str]]:
        private, public = self.service.cubes.views.get_all_names(cube_name)
        return {"private": list(private), "public": list(public)}

    @_tm1_api("get view structure")
    def get_view_structure(
        self, cube_name: str, view_name: str, private: bool = False
    ) -> dict[str, Any]:
        """Return full view structure: axis assignments with dimension-subset-element details."""
        v = self.service.cubes.views.get(cube_name, view_name, private=private)

        def _describe_axis(axis_items: list[Any]) -> list[dict[str, Any]]:
            result = []
            for item in axis_items:
                entry: dict[str, Any] = {"dimension": item.dimension_name}
                if subset := item.subset:
                    entry["subset"] = subset.name
                    if subset.is_dynamic:
                        entry["subset_type"] = "dynamic"
                        entry["expression"] = subset.expression
                    else:
                        entry["subset_type"] = "static"
                        if not isinstance(item, Axis.ViewTitleSelection):
                            entry["elements"] = subset.elements or []
                if hasattr(item, "selected"):
                    entry["selected_element"] = item.selected
                result.append(entry)
            return result

        return {
            "name": v.name,
            "cube": cube_name,
            "private": private,
            "columns": _describe_axis(v.columns) if v.columns else [],
            "rows": _describe_axis(v.rows) if v.rows else [],
            "titles": _describe_axis(v.titles) if v.titles else [],
            "suppress_empty_rows": getattr(v, "suppress_empty_rows", None),
            "suppress_empty_columns": getattr(v, "suppress_empty_columns", None),
        }

    # ------------------------------------------------------------------
    # View — write
    # ------------------------------------------------------------------

    @_tm1_api("create view")
    def create_view(
        self,
        cube_name: str,
        view_name: str,
        mdx: str,
    ) -> dict[str, Any]:
        """Create an MDX view on a cube."""
        from TM1py.Objects import MDXView
        view = MDXView(cube_name=cube_name, view_name=view_name, MDX=mdx)
        self.service.cubes.views.create(view)
        logger.info(f"Created view '{view_name}' on '{cube_name}'")
        return {"success": True, "view_name": view_name, "cube_name": cube_name}

    @_tm1_api("delete view")
    def delete_view(
        self,
        cube_name: str,
        view_name: str,
        private: bool = False,
    ) -> dict[str, Any]:
        self.service.cubes.views.delete(cube_name, view_name, private=private)
        logger.info(f"Deleted view '{view_name}' from '{cube_name}'")
        return {"success": True, "view_name": view_name, "cube_name": cube_name}

    # ------------------------------------------------------------------
    # Subset — read-only
    # ------------------------------------------------------------------

    @_tm1_api("list subsets")
    def list_subsets(
        self,
        dimension_name: str,
        hierarchy_name: str | None = None,
        private: bool = False,
    ) -> list[str]:
        hier = hierarchy_name or self.service.dimensions.hierarchies.get_all_names(
            dimension_name
        )[0]
        return self.service.dimensions.subsets.get_all_names(
            dimension_name, hierarchy_name=hier, private=private
        )

    @_tm1_api("get subset")
    def get_subset(
        self,
        dimension_name: str,
        subset_name: str,
        hierarchy_name: str | None = None,
        private: bool = False,
    ) -> dict[str, Any]:
        """Get subset details including type (static/dynamic) and MDX expression."""
        hier = hierarchy_name or self.service.dimensions.hierarchies.get_all_names(
            dimension_name
        )[0]
        s = self.service.dimensions.subsets.get(
            subset_name, dimension_name, hierarchy_name=hier, private=private
        )
        result: dict[str, Any] = {
            "name": s.name,
            "dimension": dimension_name,
            "hierarchy": hier,
            "private": private,
            "subset_type": "dynamic" if s.is_dynamic else "static",
            "element_count": len(s.elements) if s.elements else 0,
            "elements": s.elements if s.elements else [],
        }
        if s.is_dynamic:
            result["expression"] = s.expression
        return result

    # ------------------------------------------------------------------
    # Subset — write
    # ------------------------------------------------------------------

    @_tm1_api("create subset")
    def create_subset(
        self,
        dimension_name: str,
        subset_name: str,
        hierarchy_name: str | None = None,
        elements: list[str] | None = None,
        expression: str | None = None,
    ) -> dict[str, Any]:
        """Create a static or dynamic subset. Provide elements for static, expression for MDX dynamic."""
        hier = self._resolve_hierarchy(dimension_name, hierarchy_name)
        from TM1py.Objects import Subset
        subset = Subset(
            subset_name=subset_name,
            dimension_name=dimension_name,
            hierarchy_name=hier,
            elements=elements,
            expression=expression,
        )
        self.service.dimensions.subsets.create(subset)
        logger.info(f"Created subset '{subset_name}' on '{dimension_name}'")
        return {"success": True, "subset_name": subset_name, "dimension_name": dimension_name}

    @_tm1_api("update subset")
    def update_subset(
        self,
        dimension_name: str,
        subset_name: str,
        hierarchy_name: str | None = None,
        elements: list[str] | None = None,
        expression: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing subset's elements or MDX expression."""
        hier = self._resolve_hierarchy(dimension_name, hierarchy_name)
        from TM1py.Objects import Subset
        subset = Subset(
            subset_name=subset_name,
            dimension_name=dimension_name,
            hierarchy_name=hier,
            elements=elements,
            expression=expression,
        )
        self.service.dimensions.subsets.update(subset)
        logger.info(f"Updated subset '{subset_name}' on '{dimension_name}'")
        return {"success": True, "subset_name": subset_name, "dimension_name": dimension_name}

    @_tm1_api("delete subset")
    def delete_subset(
        self,
        dimension_name: str,
        subset_name: str,
        hierarchy_name: str | None = None,
    ) -> dict[str, Any]:
        hier = self._resolve_hierarchy(dimension_name, hierarchy_name)
        self.service.dimensions.subsets.delete(
            subset_name, dimension_name, hierarchy_name=hier
        )
        logger.info(f"Deleted subset '{subset_name}' from '{dimension_name}'")
        return {"success": True, "subset_name": subset_name, "dimension_name": dimension_name}

    # ------------------------------------------------------------------
    # Cell — read-only
    # ------------------------------------------------------------------

    @_tm1_api("get cell value")
    def get_cell_value(
        self,
        cube_name: str,
        elements: list[str],
        dimensions: list[str] | None = None,
    ) -> str | float:
        return self.service.cells.get_value(
            cube_name, ",".join(elements), dimensions=dimensions
        )

    @_tm1_api("execute MDX query")
    def execute_mdx(
        self,
        mdx: str | MdxBuilder,
        top: int | None = None,
        skip_zeros: bool = False,
        skip_consolidated: bool = False,
        use_blob: bool = False,
    ) -> list[dict[str, Any]]:
        """Execute an MDX query. Accepts raw MDX string or MdxBuilder object.

        MdxBuilder is recommended when constructing queries programmatically
        as it reduces MDX syntax errors. Example:
            q = MdxBuilder.from_cube(cube_name).non_empty(0)
            for dim in dimensions:
                q = q.add_hierarchy_set_to_axis(0, MdxHierarchySet.all_leaves(dim))
            result = tm1.execute_mdx(q)
        """
        result = self.service.cells.execute_mdx_dataframe(
            mdx,
            skip_zeros=skip_zeros,
            skip_consolidated_cells=skip_consolidated,
            use_blob=use_blob,
        )
        if top is not None:
            result = result.head(top)
        return result.to_dict(orient="records")

    @_tm1_api("execute view")
    def execute_view(
        self,
        cube_name: str,
        view_name: str,
        private: bool = False,
        top: int | None = None,
    ) -> list[dict[str, Any]]:
        df = self.service.cells.execute_view_dataframe(
            cube_name, view_name, private=private
        )
        if top is not None:
            df = df.head(top)
        return df.to_dict(orient="records")

    # ------------------------------------------------------------------
    # Cell — write
    # ------------------------------------------------------------------

    @_tm1_api("write cell")
    def write_cell(
        self,
        cube_name: str,
        elements: list[str],
        value: float | str,
        dimensions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Write a single cell value. Elements follow cube dimension order."""
        self.service.cells.write_value(value, cube_name, elements, dimensions=dimensions)
        logger.info(f"Wrote cell {elements} = {value} in '{cube_name}'")
        return {"success": True, "cube_name": cube_name}

    @_tm1_api("write bulk")
    def write_bulk(
        self,
        cube_name: str,
        cellset: dict[str, Any],
        dimensions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Bulk write cells. cellset keys are JSON-encoded tuples, values are numbers/strings.

        Example cellset: {"('D1E1','D2E1')": 100, "('D1E2','D2E1')": 200}
        """
        parsed: dict[tuple[str, ...], Any] = {}
        for key, val in cellset.items():
            if isinstance(key, str):
                inner = key.strip("()")
                parts = [p.strip().strip("'\"") for p in inner.split(",")]
                parsed[tuple(parts)] = val
            else:
                parsed[key] = val
        try:
            self.service.cells.write(cube_name, parsed, dimensions=dimensions, use_blob=True)
        except TM1pyException:
            self.service.cells.write(cube_name, parsed, dimensions=dimensions)
        logger.info(f"Bulk wrote {len(parsed)} cells to '{cube_name}'")
        return {"success": True, "cube_name": cube_name, "cells_written": len(parsed)}

    @_tm1_api("write file to cube")
    def write_file(
        self,
        cube_name: str,
        file_path: str,
        dimensions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Read a CSV file and write its data to a cube via dataframe."""
        resolved = self._validate_csv_path(file_path)
        import pandas as pd
        df = pd.read_csv(resolved, dtype=str)
        last_col = df.columns[-1]
        df[last_col] = df[last_col].astype(float)
        self.service.cells.write_dataframe(
            cube_name, df, dimensions=dimensions
        )
        logger.info(f"Wrote {len(df)} rows from '{file_path}' to '{cube_name}'")
        return {"success": True, "cube_name": cube_name, "rows_written": len(df)}

    @_tm1_api("clear cube")
    def clear_cube(
        self,
        cube_name: str,
        mdx_filter: str | None = None,
    ) -> dict[str, Any]:
        """Clear cube data. If mdx_filter provided, clear only matching slice."""
        if mdx_filter:
            self.service.cells.clear_with_mdx(cube_name, mdx_filter)
        else:
            try:
                self.service.cells.clear(cube_name)
            except (TM1pyException, AttributeError):
                dims = self.service.cubes.get_dimension_names(cube_name)
                mdx = f"SELECT {','.join(f'{{[{d}].Members}}' for d in dims)} ON 0 FROM [{cube_name}]"
                self.service.cells.clear_with_mdx(cube_name, mdx)
        logger.info(f"Cleared cube '{cube_name}'")
        return {"success": True, "cube_name": cube_name}

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify_dimension(
        self,
        dimension_name: str,
        expected_elements: dict[str, int] | None = None,
        expected_attributes: list[str] | None = None,
        hierarchy_name: str | None = None,
    ) -> dict[str, Any]:
        """Verify dimension structure matches expectations.

        expected_elements: {"Numeric": N, "String": S, "Consolidated": C} or None to skip.
        expected_attributes: list of attribute names that must exist, or None to skip.
        """
        try:
            info = self.get_dimension_info(dimension_name, hierarchy_name)
            differences: list[str] = []

            if expected_elements is not None:
                for etype, count in expected_elements.items():
                    actual = info["element_counts"].get(etype.lower(), 0)
                    if actual != count:
                        differences.append(
                            f"Element type '{etype}': expected {count}, got {actual}"
                        )

            if expected_attributes is not None:
                actual_attrs = set(info.get("attribute_names", []))
                for attr in expected_attributes:
                    if attr not in actual_attrs:
                        differences.append(f"Missing attribute '{attr}'")

            return {
                "dimension": dimension_name,
                "match": len(differences) == 0,
                "differences": differences,
                "actual": info,
            }
        except Exception as exc:
            return {
                "dimension": dimension_name,
                "match": False,
                "differences": [str(exc)],
                "actual": None,
            }

    def verify_cube(
        self,
        cube_name: str,
        expected_dimensions: list[str] | None = None,
        check_has_data: bool = False,
    ) -> dict[str, Any]:
        """Verify cube structure matches expectations."""
        try:
            info = self.get_cube(cube_name)
            differences: list[str] = []

            if expected_dimensions is not None:
                if info["dimensions"] != expected_dimensions:
                    differences.append(
                        f"Dimension order: expected {expected_dimensions}, "
                        f"got {info['dimensions']}"
                    )

            if check_has_data:
                dims = info["dimensions"]
                mdx = f"SELECT NON EMPTY {{[{dims[0]}].Members}} ON 0 FROM [{cube_name}]"
                result = self.execute_mdx(mdx, skip_zeros=True, top=1)
                if not result:
                    differences.append("Cube has no data")

            return {
                "cube": cube_name,
                "match": len(differences) == 0,
                "differences": differences,
                "actual": info,
            }
        except Exception as exc:
            return {
                "cube": cube_name,
                "match": False,
                "differences": [str(exc)],
                "actual": None,
            }

    # ------------------------------------------------------------------
    # Process — read
    # ------------------------------------------------------------------

    @_tm1_api("list processes")
    def list_processes(self, skip_control_processes: bool = True) -> list[str]:
        names = self.service.processes.get_all_names(
            skip_control_processes=skip_control_processes
        )
        return sorted(names)

    @_tm1_api("get process")
    def get_process(
        self, process_name: str, include_code: bool = True
    ) -> dict[str, Any]:
        p = self.service.processes.get(process_name)
        result: dict[str, Any] = {
            "name": p.name,
            "datasource_type": p.datasource_type,
            "has_security_access": p.has_security_access,
            "parameters": p.parameters or [],
            "variables": p.variables or [],
        }
        if include_code:
            result["prolog_procedure"] = p.prolog_procedure or ""
            result["metadata_procedure"] = p.metadata_procedure or ""
            result["data_procedure"] = p.data_procedure or ""
            result["epilog_procedure"] = p.epilog_procedure or ""
        return result

    @_tm1_api("search processes")
    def search_processes(
        self, keyword: str, search_code: bool = True
    ) -> list[dict[str, Any]]:
        name_matches = set(self.service.processes.search_string_in_name(keyword))
        code_matches = (
            set(self.service.processes.search_string_in_code(keyword))
            if search_code else set()
        )
        return [
            {"name": n, "match_type": "name"} for n in name_matches
        ] + [
            {"name": n, "match_type": "code"} for n in code_matches - name_matches
        ]

    @_tm1_api("compile process")
    def compile_process(self, process_name: str) -> dict[str, Any]:
        errors = self.service.processes.compile(process_name)
        return {
            "process_name": process_name,
            "has_errors": len(errors) > 0,
            "errors": errors,
        }

    @_tm1_api("get process error log")
    def get_process_error_log(self, process_name: str) -> str:
        return self.service.processes.get_last_message_from_processerrorlog(
            process_name
        )

    # ------------------------------------------------------------------
    # Process — write
    # ------------------------------------------------------------------

    def _apply_parameters_and_variables(
        self,
        process: Process,
        parameters: list[dict[str, Any]] | None,
        variables: list[dict[str, Any]] | None,
        clear_existing: bool = False,
    ) -> None:
        if parameters is not None and len(parameters) == 0:
            parameters = None
        if variables is not None and len(variables) == 0:
            variables = None
        if parameters is not None:
            if clear_existing:
                process._parameters = []
            for param in parameters:
                process.add_parameter(
                    name=param["name"],
                    prompt=param.get("prompt", ""),
                    value=param.get("value", ""),
                    parameter_type=param.get("type", "String"),
                )
        if variables is not None:
            if clear_existing:
                process._variables = []
            for var in variables:
                process.add_variable(var["name"], var.get("type", "String"))

    @_tm1_api("create process")
    def create_process(
        self,
        process_name: str,
        prolog: str = "",
        metadata: str = "",
        data: str = "",
        epilog: str = "",
        parameters: list[dict[str, Any]] | None = None,
        variables: list[dict[str, Any]] | None = None,
        datasource_type: str = "None",
    ) -> dict[str, Any]:
        p = Process(
            name=process_name,
            prolog_procedure=prolog,
            metadata_procedure=metadata,
            data_procedure=data,
            epilog_procedure=epilog,
            datasource_type=datasource_type,
        )
        self._apply_parameters_and_variables(p, parameters, variables)
        self.service.processes.create(p)
        logger.info(f"Created process '{process_name}'")
        return {"success": True, "process_name": process_name}

    @_tm1_api("update process")
    def update_process(
        self,
        process_name: str,
        prolog: str | None = None,
        metadata: str | None = None,
        data: str | None = None,
        epilog: str | None = None,
        parameters: list[dict[str, Any]] | None = None,
        variables: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        p = self.service.processes.get(process_name)
        if prolog is not None:
            p.prolog_procedure = prolog
        if metadata is not None:
            p.metadata_procedure = metadata
        if data is not None:
            p.data_procedure = data
        if epilog is not None:
            p.epilog_procedure = epilog
        self._apply_parameters_and_variables(
            p, parameters, variables, clear_existing=True
        )
        self.service.processes.update(p)
        logger.info(f"Updated process '{process_name}'")
        return {"success": True, "process_name": process_name}

    @_tm1_api("delete process")
    def delete_process(self, process_name: str) -> dict[str, Any]:
        self.service.processes.delete(process_name)
        logger.info(f"Deleted process '{process_name}'")
        return {"success": True, "process_name": process_name}

    @_tm1_api("execute process")
    def execute_process(
        self,
        process_name: str,
        parameters: list[dict[str, Any]] | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if parameters:
            for param in parameters:
                kwargs[param["name"]] = param.get("value", "")
        success, status, error_log_file = (
            self.service.processes.execute_with_return(
                process_name, timeout=timeout, **kwargs
            )
        )
        result: dict[str, Any] = {
            "success": success,
            "status": status,
            "process_name": process_name,
        }
        if error_log_file:
            result["error_log_file"] = error_log_file
        if not success and error_log_file:
            try:
                result["error_log"] = (
                    self.service.processes.get_last_message_from_processerrorlog(
                        process_name
                    )
                )
            except TM1pyException:
                result["error_log"] = "(unable to retrieve error details)"
        return result
