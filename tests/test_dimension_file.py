"""Tests for file-based dimension write methods."""

import json

import pytest

TEST_DIM = "Claude_Test_FileDim"
TEST_DIM_ADD = "Claude_Test_FileAddElem"
TEST_DIM_HIER = "Claude_Test_FileHier"
TEST_DIM_ATTR = "Claude_Test_FileAttr"


@pytest.fixture(autouse=True)
def cleanup_dimension(tm1_manager):
    """Ensure test dimensions are cleaned up before and after each test."""
    for name in [TEST_DIM, TEST_DIM_ADD, TEST_DIM_HIER, TEST_DIM_ATTR]:
        try:
            tm1_manager.delete_dimension(name)
        except Exception:
            pass
    yield
    for name in [TEST_DIM, TEST_DIM_ADD, TEST_DIM_HIER, TEST_DIM_ATTR]:
        try:
            tm1_manager.delete_dimension(name)
        except Exception:
            pass


# -- create_dimension_from_file ----------------------------------------

class TestCreateDimensionFile:

    def test_create_from_full_spec(self, tm1_manager, tmp_path):
        spec = {
            "dimension_name": TEST_DIM,
            "hierarchy_name": None,
            "elements": [
                {"name": "Total Account", "type": "Consolidated"},
                {"name": "Revenue", "type": "Numeric"},
                {"name": "Expense", "type": "Numeric"},
            ],
            "edges": [
                {"parent": "Total Account", "child": "Revenue", "weight": 1.0},
                {"parent": "Total Account", "child": "Expense", "weight": 1.0},
            ],
            "attributes": [
                {"name": "Code", "type": "String"},
                {"name": "Long Name", "type": "Alias"},
            ],
            "attribute_values": [
                {"element": "Revenue", "attribute": "Code", "value": "REV"},
                {"element": "Revenue", "attribute": "Long Name", "value": "Total Revenue"},
            ],
            "subsets": [
                {
                    "name": "All Leaves",
                    "type": "dynamic",
                    "expression": "{TM1FilterByLevel({TM1SubsetAll([" + TEST_DIM + "])}, 0)}",
                },
            ],
        }
        f = tmp_path / "spec.json"
        f.write_text(json.dumps(spec), encoding="utf-8")

        result = tm1_manager.create_dimension_from_file(str(f))
        assert result["success"] is True
        assert result["dimension_name"] == TEST_DIM
        assert result["element_count"] == 3
        assert result["attributes_created"] == 2
        assert result["attribute_values_written"] == 2
        assert result["subsets_created"] == 1

        info = tm1_manager.get_dimension_info(TEST_DIM)
        assert info["element_counts"]["total"] == 3
        assert "Code" in info["attribute_names"]
        assert "Long Name" in info["alias_names"]

        attrs = tm1_manager.get_element_attributes(
            TEST_DIM, elements=["Revenue"], attribute_names=["Code"]
        )
        assert attrs["attributes"]["Revenue"]["Code"] == "REV"

    def test_create_elements_only(self, tm1_manager, tmp_path):
        spec = {
            "dimension_name": TEST_DIM,
            "elements": [
                {"name": "A", "type": "Numeric"},
                {"name": "B", "type": "String"},
            ],
        }
        f = tmp_path / "simple.json"
        f.write_text(json.dumps(spec), encoding="utf-8")

        result = tm1_manager.create_dimension_from_file(str(f))
        assert result["success"] is True
        assert result["element_count"] == 2
        assert result["attributes_created"] == 0
        assert result["subsets_created"] == 0

        info = tm1_manager.get_dimension_info(TEST_DIM)
        assert info["element_counts"]["total"] == 2

    def test_file_not_found(self, tm1_manager, tmp_path):
        with pytest.raises(RuntimeError, match="Spec file not found"):
            tm1_manager.create_dimension_from_file(str(tmp_path / "missing.json"))


# -- add_elements_from_file --------------------------------------------

class TestAddElementsFile:

    def test_add_from_array(self, tm1_manager, tmp_path):
        tm1_manager.create_dimension(
            TEST_DIM_ADD, [{"name": "Original", "type": "Numeric"}]
        )
        elements = [
            {"name": "Added1", "type": "Numeric"},
            {"name": "Added2", "type": "String"},
        ]
        f = tmp_path / "elements.json"
        f.write_text(json.dumps(elements), encoding="utf-8")

        result = tm1_manager.add_elements_from_file(str(f), TEST_DIM_ADD)
        assert result["success"] is True
        assert result["added_count"] == 2

        info = tm1_manager.get_dimension_info(TEST_DIM_ADD)
        assert info["element_counts"]["total"] == 3

    def test_add_from_object(self, tm1_manager, tmp_path):
        tm1_manager.create_dimension(
            TEST_DIM_ADD, [{"name": "Original", "type": "Numeric"}]
        )
        data = {
            "elements": [
                {"name": "Added1", "type": "Numeric"},
            ]
        }
        f = tmp_path / "elements.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = tm1_manager.add_elements_from_file(str(f), TEST_DIM_ADD)
        assert result["success"] is True
        assert result["added_count"] == 1


# -- update_hierarchy_from_file -----------------------------------------

class TestUpdateHierarchyFile:

    def test_add_edges_from_file(self, tm1_manager, tmp_path):
        tm1_manager.create_dimension(
            TEST_DIM_HIER,
            [
                {"name": "Parent", "type": "Consolidated"},
                {"name": "Child1", "type": "Numeric"},
                {"name": "Child2", "type": "Numeric"},
            ],
        )
        data = {
            "add_edges": [
                {"parent": "Parent", "child": "Child1", "weight": 1.0},
                {"parent": "Parent", "child": "Child2", "weight": 2.0},
            ]
        }
        f = tmp_path / "edges.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = tm1_manager.update_hierarchy_from_file(str(f), TEST_DIM_HIER)
        assert result["success"] is True
        assert result["edges_added"] == 2

        parents = tm1_manager.get_parents(TEST_DIM_HIER, ["Child1", "Child2"])
        assert parents["parents"]["Child1"] == ["Parent"]
        assert parents["parents"]["Child2"] == ["Parent"]

    def test_remove_edges_from_file(self, tm1_manager, tmp_path):
        tm1_manager.create_dimension(
            TEST_DIM_HIER,
            [
                {"name": "Top", "type": "Consolidated"},
                {"name": "Leaf", "type": "Numeric"},
            ],
            edges=[{"parent": "Top", "child": "Leaf", "weight": 1.0}],
        )
        data = {
            "remove_edges": [{"parent": "Top", "child": "Leaf"}]
        }
        f = tmp_path / "edges.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = tm1_manager.update_hierarchy_from_file(str(f), TEST_DIM_HIER)
        assert result["success"] is True
        assert result["edges_removed"] == 1

        parents = tm1_manager.get_parents(TEST_DIM_HIER, ["Leaf"])
        assert parents["parents"]["Leaf"] == []


# -- write_element_attributes_from_file ---------------------------------

class TestWriteElementAttributesFile:

    def test_write_attrs_from_file(self, tm1_manager, tmp_path):
        tm1_manager.create_dimension(
            TEST_DIM_ATTR,
            [
                {"name": "Q1", "type": "Numeric"},
                {"name": "Q2", "type": "Numeric"},
            ],
        )
        tm1_manager.create_element_attribute(TEST_DIM_ATTR, "Alias", "Alias")

        attr_values = [
            {"element": "Q1", "attribute": "Alias", "value": "Quarter 1"},
            {"element": "Q2", "attribute": "Alias", "value": "Quarter 2"},
        ]
        f = tmp_path / "attrs.json"
        f.write_text(json.dumps(attr_values), encoding="utf-8")

        result = tm1_manager.write_element_attributes_from_file(
            str(f), TEST_DIM_ATTR
        )
        assert result["success"] is True
        assert result["values_updated"] == 2

        attrs = tm1_manager.get_element_attributes(
            TEST_DIM_ATTR, elements=["Q1", "Q2"], attribute_names=["Alias"]
        )
        assert attrs["attributes"]["Q1"]["Alias"] == "Quarter 1"
        assert attrs["attributes"]["Q2"]["Alias"] == "Quarter 2"

    def test_write_attrs_from_object_format(self, tm1_manager, tmp_path):
        tm1_manager.create_dimension(
            TEST_DIM_ATTR,
            [{"name": "X", "type": "Numeric"}],
        )
        tm1_manager.create_element_attribute(TEST_DIM_ATTR, "Desc", "String")

        data = {
            "attribute_values": [
                {"element": "X", "attribute": "Desc", "value": "Test Desc"},
            ]
        }
        f = tmp_path / "attrs.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = tm1_manager.write_element_attributes_from_file(
            str(f), TEST_DIM_ATTR
        )
        assert result["success"] is True
        assert result["values_updated"] == 1
