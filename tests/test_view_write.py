"""Tests for view write MCP tools."""

import pytest

TEST_DIMS = ["Claude_Test_ViewD1", "Claude_Test_ViewD2"]
TEST_CUBE = "Claude_Test_ViewCube"


@pytest.fixture(autouse=True)
def setup_cube(tm1_manager):
    """Create a test cube with dimensions before each test, clean up after."""
    for dim in TEST_DIMS:
        try:
            tm1_manager.delete_dimension(dim)
        except Exception:
            pass
        tm1_manager.create_dimension(
            dim,
            [
                {"name": "Total", "type": "Consolidated"},
                {"name": "A", "type": "Numeric"},
                {"name": "B", "type": "Numeric"},
            ],
            edges=[
                {"parent": "Total", "child": "A", "weight": 1.0},
                {"parent": "Total", "child": "B", "weight": 1.0},
            ],
        )
    try:
        tm1_manager.delete_cube(TEST_CUBE)
    except Exception:
        pass
    tm1_manager.create_cube(TEST_CUBE, TEST_DIMS)
    yield
    try:
        tm1_manager.delete_cube(TEST_CUBE)
    except Exception:
        pass
    for dim in TEST_DIMS:
        try:
            tm1_manager.delete_dimension(dim)
        except Exception:
            pass


class TestCreateView:

    def test_create_mdx_view(self, tm1_manager):
        mdx = f"SELECT NON EMPTY {{[Claude_Test_ViewD1].[A]}} ON 0, NON EMPTY {{[Claude_Test_ViewD2].[A]}} ON 1 FROM [{TEST_CUBE}]"
        result = tm1_manager.create_view(TEST_CUBE, "TestView", mdx)
        assert result["success"] is True

        views = tm1_manager.list_views(TEST_CUBE)
        assert "TestView" in views["public"]

    def test_create_view_missing_cube(self, tm1_manager):
        with pytest.raises(RuntimeError):
            tm1_manager.create_view(
                "Claude_Test_DoesNotExist", "X",
                "SELECT FROM [Claude_Test_DoesNotExist]"
            )


class TestDeleteView:

    def test_delete_view(self, tm1_manager):
        mdx = f"SELECT {{[Claude_Test_ViewD1].[A]}} ON 0 FROM [{TEST_CUBE}]"
        tm1_manager.create_view(TEST_CUBE, "TestDelView", mdx)
        result = tm1_manager.delete_view(TEST_CUBE, "TestDelView")
        assert result["success"] is True

        views = tm1_manager.list_views(TEST_CUBE)
        assert "TestDelView" not in views["public"]
