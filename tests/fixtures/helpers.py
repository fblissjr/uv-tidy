# tests/fixtures/helpers.py
import os
import json
import tempfile
import shutil
from datetime import datetime, timedelta


def create_test_file_structure(structure_dict):
    """
    Create a test file structure based on a dictionary specification.
    
    Args:
        structure_dict: Dictionary specifying the structure, e.g.,
            {
                "dir1": {
                    "file1.txt": "content",
                    "subdir": {
                        "file2.txt": "content2"
                    }
                }
            }
    
    Returns:
        Path to the temp directory containing the structure
    """
    temp_dir = tempfile.mkdtemp()
    
    def _create_structure(current_path, structure):
        for name, content in structure.items():
            path = os.path.join(current_path, name)
            if isinstance(content, dict):
                os.makedirs(path, exist_ok=True)
                _create_structure(path, content)
            else:
                with open(path, 'w') as f:
                    f.write(str(content))
    
    _create_structure(temp_dir, structure_dict)
    return temp_dir


def simulate_system_timestamps(path, timestamp_map):
    """
    Modify file timestamps to simulate specific access patterns.
    
    Args:
        path: Base path
        timestamp_map: Dictionary mapping relative paths to (atime, mtime) tuples
    """
    for rel_path, (atime, mtime) in timestamp_map.items():
        full_path = os.path.join(path, rel_path)
        if os.path.exists(full_path):
            os.utime(full_path, (atime, mtime))


def create_fake_uv_config(path, content=None):
    """
    Create a fake uv config file structure.
    
    Args:
        path: Directory to create the config in
        content: Optional content to write to the config
    
    Returns:
        Path to the config file
    """
    if content is None:
        content = {
            "venv_dirs": [
                "~/custom_venvs",
                "~/.local/share/uv/venvs"
            ],
            "excluded_patterns": [
                "*-temp",
                "*.bak"
            ],
            "min_age_days": 45,
            "min_size_mb": 10
        }
    
    config_dir = os.path.join(path, ".config", "uv")
    os.makedirs(config_dir, exist_ok=True)
    
    config_path = os.path.join(config_dir, "tidy.json")
    with open(config_path, "w") as f:
        json.dump(content, f, indent=2)
    
    return config_path


def verify_directory_removal(base_dir, expected_removed, expected_kept):
    """
    Verify that specific directories were removed and others were kept.
    
    Args:
        base_dir: Base directory to check
        expected_removed: List of directory names expected to be removed
        expected_kept: List of directory names expected to be kept
        
    Returns:
        (bool, list) - Success flag and list of errors if any
    """
    errors = []
    
    # Check that removed directories don't exist
    for dir_name in expected_removed:
        dir_path = os.path.join(base_dir, dir_name)
        if os.path.exists(dir_path):
            errors.append(f"Directory {dir_name} was not removed as expected")
    
    # Check that kept directories still exist
    for dir_name in expected_kept:
        dir_path = os.path.join(base_dir, dir_name)
        if not os.path.exists(dir_path):
            errors.append(f"Directory {dir_name} was unexpectedly removed")
    
    return not errors, errors


def simulate_cli_input(input_values):
    """
    Helper to simulate CLI user input for tests.
    
    Usage:
        with simulate_cli_input(['y', 'n']):
            # Code that will receive 'y' and then 'n' as input
    
    Args:
        input_values: List of strings to be returned by input()
    
    Returns:
        Context manager that patches builtins.input
    """
    import builtins
    from unittest.mock import patch
    
    input_values = iter(input_values)
    
    def mock_input(prompt=None):
        return next(input_values)
    
    return patch.object(builtins, 'input', mock_input)


def capture_output():
    """
    Capture stdout and stderr output for testing.
    
    Usage:
        with capture_output() as (out, err):
            print("test output")
            # out.getvalue() now contains "test output\n"
    
    Returns:
        tuple (stdout_StringIO, stderr_StringIO)
    """
    import sys
    from io import StringIO
    
    class Capture:
        def __init__(self):
            self.stdout = StringIO()
            self.stderr = StringIO()
            self._stdout = sys.stdout
            self._stderr = sys.stderr
        
        def __enter__(self):
            sys.stdout = self.stdout
            sys.stderr = self.stderr
            return self.stdout, self.stderr
        
        def __exit__(self, *args):
            sys.stdout = self._stdout
            sys.stderr = self._stderr
    
    return Capture()


def check_venv_structure_validity(path):
    """
    Check if a directory has a valid venv structure.
    
    Args:
        path: Path to check
        
    Returns:
        tuple (is_valid, issues) - Boolean and list of issues if invalid
    """
    issues = []
    
    # Check basic existence
    if not os.path.isdir(path):
        issues.append("Not a directory")
        return False, issues
    
    # Required components based on OS
    if os.name == "nt":  # Windows
        required_dirs = ["Scripts", "Lib"]
        required_files = [
            os.path.join("Scripts", "python.exe"),
            os.path.join("Scripts", "activate.bat"),
            "pyvenv.cfg"
        ]
    else:
        required_dirs = ["bin", "lib"]
        required_files = [
            os.path.join("bin", "python"),
            os.path.join("bin", "activate"),
            "pyvenv.cfg"
        ]
    
    # Check required directories
    for dir_name in required_dirs:
        dir_path = os.path.join(path, dir_name)
        if not os.path.isdir(dir_path):
            issues.append(f"Missing directory: {dir_name}")
    
    # Check required files
    for file_path in required_files:
        full_path = os.path.join(path, file_path)
        if not os.path.isfile(full_path):
            issues.append(f"Missing file: {file_path}")
    
    return len(issues) == 0, issues