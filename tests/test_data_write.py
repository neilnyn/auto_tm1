"""Tests for data write MCP tools."""

import os
import tempfile

import pytest

TEST_DIMS = ["Claude_Test_DataD1", "Claude_Test_DataD2"]
TEST_CUBE = "Claude_Test_DataCube"


@pytest.fixture(autouse=True)
def setup_cube(tm1_manager):
    """Create a test cube with dimensions and seed data."""
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


class TestWriteCell:

    def test_write_cell_numeric(self, tm1_manager):
        tm1_manager.write_cell(TEST_CUBE, ["A", "A"], 42.5)
        value = tm1_manager.get_cell_value(TEST_CUBE, ["A", "A"])
        assert value == 42.5

    def test_write_cell_string(self, tm1_manager):
        d1 = "Claude_Test_DataD1"
        d2 = "Claude_Test_DataD2"
        tm1_manager.add_elements(d1, [{"name": "Comment", "type": "String"}])
        tm1_manager.add_elements(d2, [{"name": "Note", "type": "String"}])
        tm1_manager.write_cell(TEST_CUBE, ["Comment", "Note"], "Hello TM1")
        value = tm1_manager.get_cell_value(TEST_CUBE, ["Comment", "Note"])
        assert value == "Hello TM1"

    def test_write_cell_overwrite(self, tm1_manager):
        tm1_manager.write_cell(TEST_CUBE, ["A", "A"], 10)
        tm1_manager.write_cell(TEST_CUBE, ["A", "A"], 20)
        value = tm1_manager.get_cell_value(TEST_CUBE, ["A", "A"])
        assert value == 20


class TestWriteBulk:

    def test_write_bulk(self, tm1_manager):
        cellset = {
            "('A','A')": 100,
            "('A','B')": 200,
            "('B','A')": 300,
        }
        result = tm1_manager.write_bulk(TEST_CUBE, cellset)
        assert result["success"] is True
        assert result["cells_written"] == 3

        assert tm1_manager.get_cell_value(TEST_CUBE, ["A", "A"]) == 100
        assert tm1_manager.get_cell_value(TEST_CUBE, ["A", "B"]) == 200
        assert tm1_manager.get_cell_value(TEST_CUBE, ["B", "A"]) == 300


class TestWriteFile:

    def test_write_file_csv(self, tm1_manager):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            f.write("Claude_Test_DataD1,Claude_Test_DataD2,Value\n")
            f.write("A,A,999\n")
            f.write("B,B,888\n")
            tmp_path = f.name
        try:
            result = tm1_manager.write_file(TEST_CUBE, tmp_path)
            assert result["success"] is True
            assert result["rows_written"] == 2

            assert tm1_manager.get_cell_value(TEST_CUBE, ["A", "A"]) == 999
            assert tm1_manager.get_cell_value(TEST_CUBE, ["B", "B"]) == 888
        finally:
            os.unlink(tmp_path)


class TestClearCube:

    def test_clear_cube(self, tm1_manager):
        tm1_manager.write_cell(TEST_CUBE, ["A", "A"], 100)
        tm1_manager.write_cell(TEST_CUBE, ["B", "B"], 200)

        result = tm1_manager.clear_cube(TEST_CUBE)
        assert result["success"] is True

        val1 = tm1_manager.get_cell_value(TEST_CUBE, ["A", "A"])
        assert val1 == 0 or val1 is None

    def test_clear_cube_with_filter(self, tm1_manager):
        tm1_manager.write_cell(TEST_CUBE, ["A", "A"], 100)
        tm1_manager.write_cell(TEST_CUBE, ["B", "B"], 200)

        d1, d2 = TEST_DIMS
        mdx = f"SELECT {{[{d1}].[A]}} * {{[{d2}].Members}} ON 0 FROM [{TEST_CUBE}]"
        tm1_manager.clear_cube(TEST_CUBE, mdx_filter=mdx)

        val_a = tm1_manager.get_cell_value(TEST_CUBE, ["A", "A"])
        val_b = tm1_manager.get_cell_value(TEST_CUBE, ["B", "B"])
        assert val_a == 0 or val_a is None
        assert val_b == 200
