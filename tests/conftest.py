# tests/conftest.py
import os
import shutil
import tempfile
from datetime import datetime, timedelta
import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_venv_structure():
    """
    Create a realistic venv structure.
    Returns a function that can be called to create venvs with specific attributes.
    """
    def _create_venv(base_path, name, age_days=30, is_active=False, size_kb=1000):
        """
        Create a mock venv with controllable parameters.
        
        Args:
            base_path: Base directory
            name: Name of the venv
            age_days: Age in days (affects file timestamps)
            is_active: Whether to make the venv appear active
            size_kb: Approximate size to create in KB
            
        Returns:
            Full path to the created venv
        """
        venv_path = os.path.join(base_path, name)
        
        # Create directory structure
        os.makedirs(venv_path, exist_ok=True)
        
        # Create bin/lib/include structure (or Scripts/Lib/Include on Windows)
        if os.name == "nt":  # Windows
            bin_dir = os.path.join(venv_path, "Scripts")
            lib_dir = os.path.join(venv_path, "Lib")
            include_dir = os.path.join(venv_path, "Include")
            site_packages = os.path.join(lib_dir, "site-packages")
            activate_script = os.path.join(bin_dir, "activate.bat")
            python_exe = os.path.join(bin_dir, "python.exe")
        else:  # Unix-like
            bin_dir = os.path.join(venv_path, "bin")
            lib_dir = os.path.join(venv_path, "lib")
            include_dir = os.path.join(venv_path, "include")
            site_packages = os.path.join(lib_dir, "python3.9", "site-packages")
            activate_script = os.path.join(bin_dir, "activate")
            python_exe = os.path.join(bin_dir, "python")
        
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(include_dir, exist_ok=True)
        os.makedirs(site_packages, exist_ok=True)
        
        # Create pyvenv.cfg
        with open(os.path.join(venv_path, "pyvenv.cfg"), "w") as f:
            f.write("home = /usr/bin\nversion = 3.9.0\n")
        
        # Create activation scripts with appropriate timestamps
        past_time = datetime.now() - timedelta(days=age_days)
        timestamp = past_time.timestamp()
        
        # Create activate script
        with open(activate_script, "w") as f:
            f.write("# Mock activate script\n")
        
        # Create python executable (just an empty file for testing)
        with open(python_exe, "wb") as f:
            f.write(b"\x00" * 10)
        
        # If the venv should appear active, update access time
        if is_active:
            # Access time within the last day for activate
            active_time = datetime.now() - timedelta(hours=12)
            os.utime(activate_script, (active_time.timestamp(), timestamp))
        else:
            # Set old access and modify time
            os.utime(activate_script, (timestamp, timestamp))
            os.utime(python_exe, (timestamp, timestamp))
        
        # Create some dummy files to simulate packages
        for i in range(max(1, size_kb // 10)):  # Divide by 10 to avoid too many files
            pkg_dir = os.path.join(site_packages, f"package{i}")
            os.makedirs(pkg_dir, exist_ok=True)
            
            # Create a few random files in each package
            for j in range(5):
                with open(os.path.join(pkg_dir, f"file{j}.py"), "wb") as f:
                    # Each file size will be roughly 2KB
                    f.write(b"x" * 2048)
        
        return venv_path
    
    return _create_venv


@pytest.fixture
def mock_uv_venvs(temp_dir, mock_venv_structure):
    """
    Create a set of mock uv venvs with different characteristics.
    Returns a dict of details about the created venvs.
    """
    venvs_dir = os.path.join(temp_dir, ".uv", "venvs")
    os.makedirs(venvs_dir, exist_ok=True)
    
    venvs = {
        # Name: (age_days, is_active, size_kb)
        "recent_active": (5, True, 500),
        "recent_inactive": (10, False, 800),
        "old_active": (40, True, 1200),
        "old_inactive": (60, False, 1500),
        "very_old_large": (120, False, 3000),
        "recent_tiny": (3, False, 100),
        "old_tiny": (90, False, 150),
    }
    
    created_venvs = {}
    
    for name, (age, active, size) in venvs.items():
        path = mock_venv_structure(venvs_dir, name, age, active, size)
        created_venvs[name] = {
            "path": path,
            "age_days": age,
            "is_active": active,
            "size_kb": size
        }
    
    return created_venvs