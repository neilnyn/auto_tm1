"""Tests for dimension write MCP tools."""

import pytest

TEST_DIM = "Claude_Test_DimWrite"
TEST_DIM_HIERARCHY = "Claude_Test_DimHier"


@pytest.fixture(autouse=True)
def cleanup_dimension(tm1_manager):
    """Ensure test dimension is cleaned up before and after each test."""
    for name in [TEST_DIM, TEST_DIM_HIERARCHY, "Claude_Test_AddElem",
                 "Claude_Test_DelElem", "Claude_Test_HierUpdate",
                 "Claude_Test_Attr", "Claude_Test_AttrWrite"]:
        try:
            tm1_manager.delete_dimension(name)
        except Exception:
            pass
    yield
    for name in [TEST_DIM, TEST_DIM_HIERARCHY, "Claude_Test_AddElem",
                 "Claude_Test_DelElem", "Claude_Test_HierUpdate",
                 "Claude_Test_Attr", "Claude_Test_AttrWrite"]:
        try:
            tm1_manager.delete_dimension(name)
        except Exception:
            pass


def _exists(tm1_manager, name):
    return name in tm1_manager.list_dimensions(skip_control_dims=False)


# ── create_dimension ─────────────────────────────────────────────────

class TestCreateDimension:

    def test_create_simple(self, tm1_manager):
        elements = [
            {"name": "Elem1", "type": "Numeric"},
            {"name": "Elem2", "type": "Numeric"},
            {"name": "Label1", "type": "String"},
        ]
        result = tm1_manager.create_dimension(TEST_DIM, elements)
        assert result["success"] is True
        assert result["element_count"] == 3

        info = tm1_manager.get_dimension_info(TEST_DIM)
        assert info["element_counts"]["numeric"] == 2
        assert info["element_counts"]["string"] == 1
        assert info["element_counts"]["total"] == 3

    def test_create_with_hierarchy(self, tm1_manager):
        elements = [
            {"name": "Total", "type": "Consolidated"},
            {"name": "Item1", "type": "Numeric"},
            {"name": "Item2", "type": "Numeric"},
        ]
        edges = [
            {"parent": "Total", "child": "Item1", "weight": 1.0},
            {"parent": "Total", "child": "Item2", "weight": 1.0},
        ]
        result = tm1_manager.create_dimension(
            TEST_DIM_HIERARCHY, elements, edges
        )
        assert result["success"] is True
        assert result["element_count"] == 3

        info = tm1_manager.get_dimension_info(TEST_DIM_HIERARCHY)
        assert info["element_counts"]["consolidated"] == 1
        assert info["element_counts"]["numeric"] == 2

        parents = tm1_manager.get_parents(
            TEST_DIM_HIERARCHY, ["Item1", "Item2"]
        )
        assert parents["parents"]["Item1"] == ["Total"]
        assert parents["parents"]["Item2"] == ["Total"]

    def test_create_duplicate_fails(self, tm1_manager):
        elements = [{"name": "A", "type": "Numeric"}]
        tm1_manager.create_dimension(TEST_DIM, elements)
        with pytest.raises(RuntimeError, match="already exists"):
            tm1_manager.create_dimension(TEST_DIM, elements)


# ── delete_dimension ─────────────────────────────────────────────────

class TestDeleteDimension:

    def test_delete(self, tm1_manager):
        elements = [{"name": "X", "type": "Numeric"}]
        tm1_manager.create_dimension(TEST_DIM, elements)
        assert _exists(tm1_manager, TEST_DIM)

        result = tm1_manager.delete_dimension(TEST_DIM)
        assert result["success"] is True
        assert not _exists(tm1_manager, TEST_DIM)

    def test_delete_nonexistent_fails(self, tm1_manager):
        with pytest.raises(RuntimeError):
            tm1_manager.delete_dimension("Claude_Test_DoesNotExist")


# ── add_elements ─────────────────────────────────────────────────────

class TestAddElements:

    def test_add_elements(self, tm1_manager):
        dim = "Claude_Test_AddElem"
        tm1_manager.create_dimension(
            dim, [{"name": "Original", "type": "Numeric"}]
        )
        result = tm1_manager.add_elements(
            dim,
            [
                {"name": "Added1", "type": "Numeric"},
                {"name": "Added2", "type": "String"},
            ],
        )
        assert result["success"] is True
        assert result["added_count"] == 2

        info = tm1_manager.get_dimension_info(dim)
        assert info["element_counts"]["total"] == 3


# ── delete_elements ──────────────────────────────────────────────────

class TestDeleteElements:

    def test_delete_elements(self, tm1_manager):
        dim = "Claude_Test_DelElem"
        tm1_manager.create_dimension(
            dim,
            [
                {"name": "Keep", "type": "Numeric"},
                {"name": "Remove1", "type": "Numeric"},
                {"name": "Remove2", "type": "String"},
            ],
        )
        result = tm1_manager.delete_elements(dim, ["Remove1", "Remove2"])
        assert result["success"] is True
        assert result["deleted_count"] == 2

        info = tm1_manager.get_dimension_info(dim)
        assert info["element_counts"]["total"] == 1


# ── update_hierarchy ─────────────────────────────────────────────────

class TestUpdateHierarchy:

    def test_add_edges(self, tm1_manager):
        dim = "Claude_Test_HierUpdate"
        tm1_manager.create_dimension(
            dim,
            [
                {"name": "Parent", "type": "Consolidated"},
                {"name": "Child1", "type": "Numeric"},
                {"name": "Child2", "type": "Numeric"},
            ],
        )
        result = tm1_manager.update_hierarchy(
            dim,
            add_edges=[
                {"parent": "Parent", "child": "Child1", "weight": 1.0},
                {"parent": "Parent", "child": "Child2", "weight": 2.0},
            ],
        )
        assert result["success"] is True
        assert result["edges_added"] == 2

        parents = tm1_manager.get_parents(dim, ["Child1", "Child2"])
        assert parents["parents"]["Child1"] == ["Parent"]

    def test_remove_edges(self, tm1_manager):
        dim = "Claude_Test_HierUpdate"
        tm1_manager.create_dimension(
            dim,
            [
                {"name": "Top", "type": "Consolidated"},
                {"name": "Leaf", "type": "Numeric"},
            ],
            edges=[{"parent": "Top", "child": "Leaf", "weight": 1.0}],
        )
        result = tm1_manager.update_hierarchy(
            dim,
            remove_edges=[{"parent": "Top", "child": "Leaf"}],
        )
        assert result["success"] is True
        assert result["edges_removed"] == 1

        parents = tm1_manager.get_parents(dim, ["Leaf"])
        assert parents["parents"]["Leaf"] == []


# ── create_element_attribute ─────────────────────────────────────────

class TestCreateElementAttribute:

    def test_create_attribute(self, tm1_manager):
        dim = "Claude_Test_Attr"
        tm1_manager.create_dimension(
            dim, [{"name": "A", "type": "Numeric"}]
        )
        result = tm1_manager.create_element_attribute(
            dim, "TestAlias", "Alias"
        )
        assert result["success"] is True

        info = tm1_manager.get_dimension_info(dim)
        assert "TestAlias" in info["alias_names"]


# ── write_element_attributes ─────────────────────────────────────────

class TestWriteElementAttributes:

    def test_write_attributes(self, tm1_manager):
        dim = "Claude_Test_AttrWrite"
        tm1_manager.create_dimension(
            dim,
            [
                {"name": "Q1", "type": "Numeric"},
                {"name": "Q2", "type": "Numeric"},
            ],
        )
        tm1_manager.create_element_attribute(dim, "Alias", "Alias")

        result = tm1_manager.write_element_attributes(
            dim,
            [
                {"element": "Q1", "attribute": "Alias", "value": "Quarter 1"},
                {"element": "Q2", "attribute": "Alias", "value": "Quarter 2"},
            ],
        )
        assert result["success"] is True
        assert result["values_updated"] == 2

        attrs = tm1_manager.get_element_attributes(
            dim, elements=["Q1", "Q2"], attribute_names=["Alias"]
        )
        assert attrs["attributes"]["Q1"]["Alias"] == "Quarter 1"
        assert attrs["attributes"]["Q2"]["Alias"] == "Quarter 2"
