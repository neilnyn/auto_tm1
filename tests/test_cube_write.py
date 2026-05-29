"""Tests for cube write MCP tools."""

import pytest

TEST_DIMS = ["Claude_Test_CubeD1", "Claude_Test_CubeD2", "Claude_Test_CubeD3"]
TEST_CUBE = "Claude_Test_Cube"


@pytest.fixture(autouse=True)
def setup_dimensions(tm1_manager):
    """Create test dimensions before each test, clean up after."""
    for dim in TEST_DIMS:
        try:
            tm1_manager.delete_dimension(dim)
        except Exception:
            pass
        tm1_manager.create_dimension(
            dim, [{"name": "Elem1", "type": "Numeric"}]
        )
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


class TestCreateCube:

    def test_create_cube(self, tm1_manager):
        result = tm1_manager.create_cube(TEST_CUBE, TEST_DIMS)
        assert result["success"] is True
        assert result["dimensions"] == TEST_DIMS

        cube = tm1_manager.get_cube(TEST_CUBE)
        assert cube["dimensions"] == TEST_DIMS

    def test_create_cube_wrong_dimension(self, tm1_manager):
        with pytest.raises(RuntimeError):
            tm1_manager.create_cube(
                "Claude_Test_Bad", ["Claude_Test_DoesNotExist"]
            )


class TestDeleteCube:

    def test_delete_cube(self, tm1_manager):
        tm1_manager.create_cube(TEST_CUBE, TEST_DIMS)
        result = tm1_manager.delete_cube(TEST_CUBE)
        assert result["success"] is True
        assert TEST_CUBE not in tm1_manager.list_cubes(skip_control_cubes=False)
