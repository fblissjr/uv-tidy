# tests/test_utils.py
import os
import platform
import pytest
from uv_tidy.utils import get_dir_size, is_venv_active, get_default_venv_dirs, filter_paths, format_size


def test_get_dir_size(temp_dir):
    """Test calculating directory size."""
    test_dir = os.path.join(temp_dir, "size_test")
    os.makedirs(test_dir)
    
    # Create files with known sizes
    with open(os.path.join(test_dir, "file1.txt"), "wb") as f:
        f.write(b"x" * 1024)  # 1KB
    
    with open(os.path.join(test_dir, "file2.txt"), "wb") as f:
        f.write(b"x" * 2048)  # 2KB
    
    # Create nested directory
    nested_dir = os.path.join(test_dir, "nested")
    os.makedirs(nested_dir)
    
    with open(os.path.join(nested_dir, "file3.txt"), "wb") as f:
        f.write(b"x" * 4096)  # 4KB
    
    # Total should be 7KB
    size = get_dir_size(test_dir)
    assert size == 7168, f"Expected 7168 bytes, got {size}"


def test_is_venv_active(mock_uv_venvs):
    """Test detection of active venvs."""
    for name, details in mock_uv_venvs.items():
        result = is_venv_active(details["path"])
        # Result should match what we set up in the fixture
        expected = details["is_active"]
        assert result == expected, f"Wrong active detection for {name}: got {result}, expected {expected}"


def test_get_default_venv_dirs():
    """Test getting default venv directories."""
    dirs = get_default_venv_dirs()
    
    # Should always return a list
    assert isinstance(dirs, list), "Expected a list of directories"
    
    # Should return non-empty list
    assert len(dirs) > 0, "Expected at least one default directory"
    
    # All paths should be absolute
    for d in dirs:
        if d:  # Skip empty strings
            assert os.path.isabs(d), f"Expected absolute path, got {d}"


def test_filter_paths():
    """Test filtering paths with patterns."""
    test_paths = [
        "/home/user/.uv/venvs/project1",
        "/home/user/.uv/venvs/test_venv",
        "/home/user/.uv/venvs/myapp-dev",
        "/home/user/.uv/venvs/myapp-prod",
    ]
    
    # Test with single pattern
    filtered = filter_paths(test_paths, ["*test*"])
    assert len(filtered) == 3, f"Expected 3 paths, got {len(filtered)}"
    assert "/home/user/.uv/venvs/test_venv" not in filtered, "Pattern match should be excluded"
    
    # Test with multiple patterns
    filtered = filter_paths(test_paths, ["*test*", "*dev"])
    assert len(filtered) == 2, f"Expected 2 paths, got {len(filtered)}"
    assert "/home/user/.uv/venvs/test_venv" not in filtered, "Pattern match should be excluded"
    assert "/home/user/.uv/venvs/myapp-dev" not in filtered, "Pattern match should be excluded"
    
    # Test with no matches
    filtered = filter_paths(test_paths, ["*nonexistent*"])
    assert len(filtered) == 4, f"Expected all 4 paths, got {len(filtered)}"
    
    # Test with empty list
    filtered = filter_paths(test_paths, [])
    assert len(filtered) == 4, f"Expected all 4 paths, got {len(filtered)}"


def test_format_size():
    """Test human-readable size formatting."""
    assert format_size(500) == "500 B", "Wrong format for bytes"
    assert format_size(1500) == "1.5 KB", "Wrong format for kilobytes"
    assert format_size(1500000) == "1.4 MB", "Wrong format for megabytes"
    assert format_size(1500000000) == "1.40 GB", "Wrong format for gigabytes"