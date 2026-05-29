"""Tests for subset write MCP tools."""

import pytest

TEST_DIM = "Claude_Test_Subset"


@pytest.fixture(autouse=True)
def setup_dimension(tm1_manager):
    """Create a test dimension with elements before each test, clean up after."""
    try:
        tm1_manager.delete_dimension(TEST_DIM)
    except Exception:
        pass
    tm1_manager.create_dimension(
        TEST_DIM,
        [
            {"name": "Total", "type": "Consolidated"},
            {"name": "A", "type": "Numeric"},
            {"name": "B", "type": "Numeric"},
            {"name": "C", "type": "Numeric"},
        ],
        edges=[
            {"parent": "Total", "child": "A", "weight": 1.0},
            {"parent": "Total", "child": "B", "weight": 1.0},
            {"parent": "Total", "child": "C", "weight": 1.0},
        ],
    )
    yield
    try:
        tm1_manager.delete_dimension(TEST_DIM)
    except Exception:
        pass


class TestCreateSubset:

    def test_create_static(self, tm1_manager):
        result = tm1_manager.create_subset(
            TEST_DIM, "TestStatic", elements=["A", "B"]
        )
        assert result["success"] is True

        sub = tm1_manager.get_subset(TEST_DIM, "TestStatic")
        assert sub["subset_type"] == "static"
        assert sub["element_count"] == 2
        assert "A" in sub["elements"]

    def test_create_dynamic(self, tm1_manager):
        mdx = f"{{TM1FilterByLevel({{TM1SubsetAll([{TEST_DIM}])}}, 0)}}"
        result = tm1_manager.create_subset(
            TEST_DIM, "TestDynamic", expression=mdx
        )
        assert result["success"] is True

        sub = tm1_manager.get_subset(TEST_DIM, "TestDynamic")
        assert sub["subset_type"] == "dynamic"
        assert sub["expression"] == mdx

    def test_create_missing_dimension_fails(self, tm1_manager):
        with pytest.raises(RuntimeError):
            tm1_manager.create_subset(
                "Claude_Test_DoesNotExist", "X", elements=["A"]
            )


class TestUpdateSubset:

    def test_update_elements(self, tm1_manager):
        tm1_manager.create_subset(TEST_DIM, "TestUpd", elements=["A"])
        tm1_manager.update_subset(TEST_DIM, "TestUpd", elements=["A", "B", "C"])

        sub = tm1_manager.get_subset(TEST_DIM, "TestUpd")
        assert sub["element_count"] == 3


class TestDeleteSubset:

    def test_delete(self, tm1_manager):
        tm1_manager.create_subset(TEST_DIM, "TestDel", elements=["A"])
        result = tm1_manager.delete_subset(TEST_DIM, "TestDel")
        assert result["success"] is True

        subs = tm1_manager.list_subsets(TEST_DIM)
        assert "TestDel" not in subs
