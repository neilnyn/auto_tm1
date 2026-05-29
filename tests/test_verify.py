"""Tests for verification MCP tools."""

import pytest

TEST_DIM = "Claude_Test_VerifyDim"
TEST_DIMS_CUBE = ["Claude_Test_VerifyD1", "Claude_Test_VerifyD2"]
TEST_CUBE = "Claude_Test_VerifyCube"


@pytest.fixture(autouse=True)
def cleanup(tm1_manager):
    yield
    try:
        tm1_manager.delete_cube(TEST_CUBE)
    except Exception:
        pass
    for dim in TEST_DIMS_CUBE + [TEST_DIM]:
        try:
            tm1_manager.delete_dimension(dim)
        except Exception:
            pass


class TestVerifyDimension:

    def test_verify_match(self, tm1_manager):
        tm1_manager.create_dimension(
            TEST_DIM,
            [
                {"name": "Total", "type": "Consolidated"},
                {"name": "A", "type": "Numeric"},
                {"name": "B", "type": "String"},
            ],
            edges=[{"parent": "Total", "child": "A", "weight": 1.0}],
        )
        result = tm1_manager.verify_dimension(
            TEST_DIM,
            expected_elements={"Numeric": 1, "String": 1, "Consolidated": 1},
        )
        assert result["match"] is True
        assert result["differences"] == []

    def test_verify_mismatch_element_count(self, tm1_manager):
        tm1_manager.create_dimension(
            TEST_DIM,
            [{"name": "A", "type": "Numeric"}, {"name": "B", "type": "Numeric"}],
        )
        result = tm1_manager.verify_dimension(
            TEST_DIM,
            expected_elements={"Numeric": 5},
        )
        assert result["match"] is False
        assert any("Numeric" in d for d in result["differences"])

    def test_verify_missing_attribute(self, tm1_manager):
        tm1_manager.create_dimension(
            TEST_DIM, [{"name": "X", "type": "Numeric"}]
        )
        result = tm1_manager.verify_dimension(
            TEST_DIM,
            expected_attributes=["MissingAlias"],
        )
        assert result["match"] is False
        assert any("MissingAlias" in d for d in result["differences"])

    def test_verify_missing_dimension(self, tm1_manager):
        result = tm1_manager.verify_dimension("Claude_Test_DoesNotExist")
        assert result["match"] is False


class TestVerifyCube:

    def test_verify_match(self, tm1_manager):
        for dim in TEST_DIMS_CUBE:
            tm1_manager.create_dimension(
                dim, [{"name": "E1", "type": "Numeric"}]
            )
        tm1_manager.create_cube(TEST_CUBE, TEST_DIMS_CUBE)

        result = tm1_manager.verify_cube(
            TEST_CUBE,
            expected_dimensions=TEST_DIMS_CUBE,
        )
        assert result["match"] is True

    def test_verify_wrong_dimension_order(self, tm1_manager):
        for dim in TEST_DIMS_CUBE:
            tm1_manager.create_dimension(
                dim, [{"name": "E1", "type": "Numeric"}]
            )
        tm1_manager.create_cube(TEST_CUBE, TEST_DIMS_CUBE)

        result = tm1_manager.verify_cube(
            TEST_CUBE,
            expected_dimensions=list(reversed(TEST_DIMS_CUBE)),
        )
        assert result["match"] is False
        assert any("Dimension order" in d for d in result["differences"])

    def test_verify_missing_cube(self, tm1_manager):
        result = tm1_manager.verify_cube("Claude_Test_DoesNotExist")
        assert result["match"] is False
