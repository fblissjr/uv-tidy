# tests/test_core.py
import os
import shutil
import pytest
from uv_tidy.core import find_venvs, is_uv_venv, evaluate_venv, remove_venv


def test_is_uv_venv(mock_uv_venvs):
    """Test the venv detection function."""
    # Should identify real venvs
    for name, details in mock_uv_venvs.items():
        assert is_uv_venv(details["path"]) == True, f"Failed to identify {name} as venv"
    
    # Should not identify non-venvs
    parent_dir = os.path.dirname(os.path.dirname(list(mock_uv_venvs.values())[0]["path"]))
    assert is_uv_venv(parent_dir) == False, "Incorrectly identified parent dir as venv"


def test_find_venvs(mock_uv_venvs):
    """Test finding venvs in a directory."""
    # Get the parent directory containing all mock venvs
    venvs_dir = os.path.dirname(list(mock_uv_venvs.values())[0]["path"])
    
    # Find all venvs in the directory with default settings
    found_venvs = find_venvs(venvs_dir)
    
    # Should find all the venvs we created
    assert len(found_venvs) == len(mock_uv_venvs), f"Found {len(found_venvs)} venvs, expected {len(mock_uv_venvs)}"
    
    # All found paths should exist
    for path in found_venvs:
        assert os.path.exists(path), f"Found venv {path} does not exist"
    
    # Each created venv should be in the found list
    for name, details in mock_uv_venvs.items():
        assert details["path"] in found_venvs, f"Failed to find venv {name}"


def test_find_venvs_depth_limit(mock_uv_venvs, tmp_path):
    """Test depth limiting when finding venvs."""
    # Create a nested directory structure
    nested_dir = tmp_path / "level1" / "level2" / "level3"
    nested_dir.mkdir(parents=True)
    
    # Get a sample venv and copy it to the nested location
    sample_venv_path = list(mock_uv_venvs.values())[0]["path"]
    nested_venv = nested_dir / "test_venv"
    
    # Copy the sample venv to the nested location
    shutil.copytree(sample_venv_path, nested_venv)
    
    # Test with different max depths
    
    # Depth 1 shouldn't find the nested venv
    found_depth1 = find_venvs(tmp_path, max_depth=1)
    assert nested_venv not in found_depth1, "Shouldn't find venv at depth 3 with max_depth=1"
    
    # Depth 4 should find the nested venv
    found_depth4 = find_venvs(tmp_path, max_depth=4)
    assert str(nested_venv) in found_depth4, "Should find venv at depth 3 with max_depth=4"


def test_find_venvs_exclude_dirs(mock_uv_venvs, tmp_path):
    """Test excluding directories when finding venvs."""
    # Create a directory structure with a venv in an exclude directory
    exclude_dir = tmp_path / "node_modules"
    exclude_dir.mkdir()
    
    # Get a sample venv and copy it to the excluded location
    sample_venv_path = list(mock_uv_venvs.values())[0]["path"]
    excluded_venv = exclude_dir / "test_venv"
    
    # Copy the sample venv to the excluded location
    shutil.copytree(sample_venv_path, excluded_venv)
    
    # Another venv in a non-excluded location
    normal_venv = tmp_path / "normal_venv"
    shutil.copytree(sample_venv_path, normal_venv)
    
    # Find with default exclude dirs (should exclude node_modules)
    found_venvs = find_venvs(tmp_path)
    assert str(normal_venv) in found_venvs, "Should find venv in normal location"
    assert str(excluded_venv) not in found_venvs, "Shouldn't find venv in excluded directory"
    
    # Find with custom exclude dirs
    found_custom = find_venvs(tmp_path, exclude_dirs=["normal_venv"])
    assert str(normal_venv) not in found_custom, "Shouldn't find excluded venv"
    assert str(excluded_venv) in found_custom, "Should find venv when not in exclude list"


def test_evaluate_venv_age_criteria(mock_uv_venvs):
    """Test evaluating venvs with age criteria."""
    criteria = {"min_age_days": 30, "unused_only": False}
    
    for name, details in mock_uv_venvs.items():
        result = evaluate_venv(details["path"], criteria)
        
        # Should mark old venvs for removal and keep recent ones
        if details["age_days"] >= 30:
            assert result["status"] == "remove", f"Expected to remove {name} due to age"
        else:
            assert result["status"] == "keep", f"Expected to keep {name} due to age"


def test_evaluate_venv_active_criteria(mock_uv_venvs):
    """Test evaluating venvs with active-only criteria."""
    criteria = {"min_age_days": 0, "unused_only": True}
    
    for name, details in mock_uv_venvs.items():
        result = evaluate_venv(details["path"], criteria)
        
        # Should keep active venvs and remove inactive ones
        if details["is_active"]:
            assert result["status"] == "keep", f"Expected to keep active venv {name}"


def test_evaluate_venv_size_criteria(mock_uv_venvs):
    """Test evaluating venvs with size criteria."""
    criteria = {"min_age_days": 0, "unused_only": False, "min_size_mb": 1}
    
    for name, details in mock_uv_venvs.items():
        result = evaluate_venv(details["path"], criteria)
        
        # Should mark large venvs for removal and keep small ones
        expected_size_mb = details["size_kb"] / 1024
        if expected_size_mb >= 1:
            assert result["status"] == "remove", f"Expected to remove {name} due to size"
        else:
            assert result["status"] == "keep", f"Expected to keep {name} due to size"


def test_evaluate_venv_combined_criteria(mock_uv_venvs):
    """Test evaluating venvs with combined criteria."""
    # Only remove old, inactive, large venvs
    criteria = {"min_age_days": 30, "unused_only": True, "min_size_mb": 1}
    
    for name, details in mock_uv_venvs.items():
        result = evaluate_venv(details["path"], criteria)
        
        # Should keep venvs that don't meet all criteria
        if details["age_days"] >= 30 and not details["is_active"] and details["size_kb"] >= 1024:
            assert result["status"] == "remove", f"Expected to remove {name}"
        else:
            assert result["status"] == "keep", f"Expected to keep {name}"


def test_remove_venv(temp_dir):
    """Test removing a venv."""
    # Create a test directory to remove
    test_dir = os.path.join(temp_dir, "test_remove_dir")
    os.makedirs(test_dir)
    
    # Create a file inside
    with open(os.path.join(test_dir, "test.txt"), "w") as f:
        f.write("test content")
    
    # Remove should return True for success
    assert remove_venv(test_dir) == True, "Failed to remove directory"
    
    # Directory should no longer exist
    assert not os.path.exists(test_dir), "Directory still exists after removal"
    
    # Should return False for non-existent directory
    assert remove_venv(test_dir) == False, "Remove should return False for non-existent dir"