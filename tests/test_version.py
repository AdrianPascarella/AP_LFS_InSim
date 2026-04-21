"""Tests for version parsing and constraint checking in InSimLoader."""
import pytest
from lfs_insim.insim_loader import _parse_version, _check_version


class TestParseVersion:
    def test_full_semver(self):
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_missing_patch(self):
        assert _parse_version("1.2") == (1, 2, 0)

    def test_major_only(self):
        assert _parse_version("2") == (2, 0, 0)

    def test_zeros(self):
        assert _parse_version("0.0.0") == (0, 0, 0)

    def test_large_numbers(self):
        assert _parse_version("10.20.30") == (10, 20, 30)

    def test_strips_whitespace(self):
        assert _parse_version("  1.2.3  ") == (1, 2, 3)

    def test_dash_separator(self):
        assert _parse_version("1.2-3") == (1, 2, 3)

    def test_non_numeric_part_becomes_zero(self):
        assert _parse_version("1.2.alpha") == (1, 2, 0)


class TestCheckVersion:
    def test_gte_satisfied(self):
        assert _check_version("1.2.3", ">=1.0.0") is True

    def test_gte_equal(self):
        assert _check_version("1.0.0", ">=1.0.0") is True

    def test_gte_not_satisfied(self):
        assert _check_version("0.9.9", ">=1.0.0") is False

    def test_lte_satisfied(self):
        assert _check_version("0.9.0", "<=1.0.0") is True

    def test_lte_equal(self):
        assert _check_version("1.0.0", "<=1.0.0") is True

    def test_lte_not_satisfied(self):
        assert _check_version("1.1.0", "<=1.0.0") is False

    def test_gt_satisfied(self):
        assert _check_version("2.0.0", ">1.0.0") is True

    def test_gt_not_satisfied_equal(self):
        assert _check_version("1.0.0", ">1.0.0") is False

    def test_lt_satisfied(self):
        assert _check_version("0.5.0", "<1.0.0") is True

    def test_lt_not_satisfied_equal(self):
        assert _check_version("1.0.0", "<1.0.0") is False

    def test_eq_satisfied(self):
        assert _check_version("1.2.3", "==1.2.3") is True

    def test_eq_not_satisfied(self):
        assert _check_version("1.2.4", "==1.2.3") is False

    def test_ne_satisfied(self):
        assert _check_version("1.2.4", "!=1.2.3") is True

    def test_ne_not_satisfied(self):
        assert _check_version("1.2.3", "!=1.2.3") is False

    def test_no_operator_means_exact(self):
        assert _check_version("1.0.0", "1.0.0") is True
        assert _check_version("1.0.1", "1.0.0") is False

    def test_empty_constraint_always_passes(self):
        assert _check_version("0.0.1", "") is True

    def test_patch_comparison(self):
        assert _check_version("1.0.2", ">=1.0.1") is True
        assert _check_version("1.0.0", ">=1.0.1") is False
