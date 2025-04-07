# tests/test_rules.py
import pytest
from uv_tidy.rules import make_criteria, sort_venvs_by_criteria, prune_candidates, auto_adjust_criteria


def test_make_criteria():
    """Test creating criteria from arguments."""
    # Test with default args
    args = {"min_age_days": 30, "unused_only": True}
    criteria = make_criteria(args)
    assert criteria["min_age_days"] == 30, "Wrong min_age_days"
    assert criteria["unused_only"] == True, "Wrong unused_only"
    assert "min_size_mb" not in criteria, "min_size_mb should not be included"
    
    # Test with size specified
    args = {"min_age_days": 30, "unused_only": True, "min_size_mb": 50}
    criteria = make_criteria(args)
    assert criteria["min_size_mb"] == 50, "Wrong min_size_mb"


def test_sort_venvs_by_criteria():
    """Test sorting venvs by different criteria."""
    venvs = [
        {"name": "venv1", "age_days": 10, "size_bytes": 1000, "last_accessed": "2023-01-01"},
        {"name": "venv2", "age_days": 30, "size_bytes": 5000, "last_accessed": "2023-02-01"},
        {"name": "venv3", "age_days": 20, "size_bytes": 3000, "last_accessed": "2023-03-01"},
    ]
    
    # Sort by age (descending)
    sorted_by_age = sort_venvs_by_criteria(venvs, "age")
    assert sorted_by_age[0]["name"] == "venv2", "Wrong order when sorting by age"
    assert sorted_by_age[1]["name"] == "venv3", "Wrong order when sorting by age"
    assert sorted_by_age[2]["name"] == "venv1", "Wrong order when sorting by age"
    
    # Sort by size (descending)
    sorted_by_size = sort_venvs_by_criteria(venvs, "size")
    assert sorted_by_size[0]["name"] == "venv2", "Wrong order when sorting by size"
    assert sorted_by_size[1]["name"] == "venv3", "Wrong order when sorting by size"
    assert sorted_by_size[2]["name"] == "venv1", "Wrong order when sorting by size"
    
    # Sort by name (ascending)
    sorted_by_name = sort_venvs_by_criteria(venvs, "name")
    assert sorted_by_name[0]["name"] == "venv1", "Wrong order when sorting by name"
    assert sorted_by_name[1]["name"] == "venv2", "Wrong order when sorting by name"
    assert sorted_by_name[2]["name"] == "venv3", "Wrong order when sorting by name"
    
    # Sort by accessed (descending)
    sorted_by_accessed = sort_venvs_by_criteria(venvs, "accessed")
    assert sorted_by_accessed[0]["name"] == "venv3", "Wrong order when sorting by accessed"
    assert sorted_by_accessed[1]["name"] == "venv2", "Wrong order when sorting by accessed"
    assert sorted_by_accessed[2]["name"] == "venv1", "Wrong order when sorting by accessed"
    
    # Test with missing keys
    venvs_missing_keys = [
        {"name": "venv1"}, 
        {"name": "venv2", "age_days": 30},
        {"name": "venv3", "size_bytes": 3000},
    ]
    
    # Should not crash with missing keys
    sorted_missing = sort_venvs_by_criteria(venvs_missing_keys, "age")
    assert len(sorted_missing) == 3, "Wrong number of venvs after sorting with missing keys"
    
    # Test with empty list
    sorted_empty = sort_venvs_by_criteria([], "age")
    assert sorted_empty == [], "Expected empty list when sorting empty list"


def test_prune_candidates():
    """Test limiting the number of venvs to remove."""
    venvs = [
        {"name": "venv1", "status": "remove"},
        {"name": "venv2", "status": "keep"},
        {"name": "venv3", "status": "remove"},
        {"name": "venv4", "status": "remove"},
        {"name": "venv5", "status": "error"},
    ]
    
    # Test with no limit
    pruned = prune_candidates(venvs)
    assert len(pruned) == 3, "Expected 3 venvs to remove"
    
    # Test with limit = 2
    pruned = prune_candidates(venvs, 2)
    assert len(pruned) == 2, "Expected 2 venvs after pruning"
    assert pruned[0]["name"] == "venv1", "Wrong order after pruning"
    assert pruned[1]["name"] == "venv3", "Wrong order after pruning"
    
    # Test with limit > number of removable venvs
    pruned = prune_candidates(venvs, 10)
    assert len(pruned) == 3, "Expected all 3 removable venvs"


def test_auto_adjust_criteria():
    """Test automatically adjusting criteria to target a number of venvs."""
    venvs = [
        {"name": "venv1", "age_days": 5},
        {"name": "venv2", "age_days": 10},
        {"name": "venv3", "age_days": 15},
        {"name": "venv4", "age_days": 20},
        {"name": "venv5", "age_days": 30},
        {"name": "venv6", "age_days": 60},
        {"name": "venv7", "age_days": 90},
    ]
    
    # Target 3 venvs
    criteria = auto_adjust_criteria(venvs, 3)
    assert criteria["min_age_days"] == 30, f"Expected threshold of 30 days, got {criteria['min_age_days']}"
    assert criteria["unused_only"] == True, "Expected unused_only to be True"
    
    # Target too many venvs
    criteria = auto_adjust_criteria(venvs, 10)
    assert criteria["min_age_days"] == 7, "Expected minimum threshold for excessive target"
    
    # Target 0 venvs
    criteria = auto_adjust_criteria(venvs, 0)
    assert criteria["min_age_days"] == 7, "Expected minimum threshold for zero target"
    
    # Empty venv list
    criteria = auto_adjust_criteria([], 5)
    assert criteria["min_age_days"] == 7, "Expected minimum threshold for empty list"