# tests/fixtures/mock_venvs.py
import os
import json
import shutil
import tempfile
from datetime import datetime, timedelta


def create_complex_venv_structure(base_dir, config_file=None):
    """
    Create a more complex venv structure based on a configuration file
    or default complex settings.
    
    Args:
        base_dir: Base directory to create venvs in
        config_file: Optional path to a JSON configuration file
    
    Returns:
        Dictionary with details of created venvs
    """
    # Load configuration if provided
    if config_file and os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        # Default complex configuration
        config = {
            "venvs": [
                {
                    "name": "project-with-history",
                    "age_days": 120,
                    "is_active": False,
                    "size_kb": 5000,
                    "packages": ["django", "requests", "sqlalchemy"],
                    "has_git": True,
                    "has_uncommitted_changes": True
                },
                {
                    "name": "ml-environment",
                    "age_days": 45,
                    "is_active": True,
                    "size_kb": 12000,
                    "packages": ["numpy", "pandas", "scikit-learn", "tensorflow"],
                    "has_git": False
                },
                {
                    "name": "corrupted-venv",
                    "age_days": 90,
                    "is_active": False,
                    "size_kb": 2000,
                    "is_corrupted": True,
                    "corruption_type": "missing_python"
                }
            ]
        }
    
    # Create each venv with its specific properties
    results = {}
    for venv_config in config["venvs"]:
        venv_path = os.path.join(base_dir, venv_config["name"])
        
        # Create basic structure first
        _create_basic_venv_structure(
            venv_path, 
            venv_config.get("age_days", 30), 
            venv_config.get("is_active", False)
        )
        
        # Add packages
        if "packages" in venv_config:
            _add_packages_to_venv(
                venv_path, 
                venv_config["packages"], 
                venv_config.get("size_kb", 1000) // len(venv_config["packages"])
            )
        
        # Add git repository if specified
        if venv_config.get("has_git", False):
            _add_git_repo(
                venv_path, 
                venv_config.get("has_uncommitted_changes", False)
            )
        
        # Create corruption if specified
        if venv_config.get("is_corrupted", False):
            _corrupt_venv(
                venv_path, 
                venv_config.get("corruption_type", "missing_python")
            )
        
        # Record details
        results[venv_config["name"]] = {
            "path": venv_path,
            "age_days": venv_config.get("age_days", 30),
            "is_active": venv_config.get("is_active", False),
            "size_kb": venv_config.get("size_kb", 1000),
            "config": venv_config
        }
    
    return results


def _create_basic_venv_structure(venv_path, age_days, is_active):
    """Create basic venv directory structure."""
    os.makedirs(venv_path, exist_ok=True)
    
    # Set up timestamps
    past_time = datetime.now() - timedelta(days=age_days)
    timestamp = past_time.timestamp()
    
    # Create OS-specific structure
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
    
    # Create directories
    os.makedirs(bin_dir, exist_ok=True)
    os.makedirs(lib_dir, exist_ok=True)
    os.makedirs(include_dir, exist_ok=True)
    os.makedirs(site_packages, exist_ok=True)
    
    # Create pyvenv.cfg
    with open(os.path.join(venv_path, "pyvenv.cfg"), "w") as f:
        f.write("home = /usr/bin\nversion = 3.9.0\n")
    
    # Create activate script
    with open(activate_script, "w") as f:
        f.write("# Mock activate script\n")
    
    # Create python executable
    with open(python_exe, "wb") as f:
        f.write(b"\x00" * 10)
    
    # Set file timestamps
    os.utime(venv_path, (timestamp, timestamp))
    os.utime(bin_dir, (timestamp, timestamp))
    os.utime(lib_dir, (timestamp, timestamp))
    os.utime(include_dir, (timestamp, timestamp))
    
    # If active, update access time of activate script
    if is_active:
        active_time = datetime.now() - timedelta(hours=12)
        os.utime(activate_script, (active_time.timestamp(), timestamp))
    else:
        os.utime(activate_script, (timestamp, timestamp))
        os.utime(python_exe, (timestamp, timestamp))


def _add_packages_to_venv(venv_path, packages, size_per_package):
    """Add mock packages to the venv."""
    if os.name == "nt":
        site_packages = os.path.join(venv_path, "Lib", "site-packages")
    else:
        site_packages = os.path.join(venv_path, "lib", "python3.9", "site-packages")
    
    for pkg in packages:
        pkg_dir = os.path.join(site_packages, pkg)
        os.makedirs(pkg_dir, exist_ok=True)
        
        # Create __init__.py
        with open(os.path.join(pkg_dir, "__init__.py"), "w") as f:
            f.write(f"# {pkg} package\n")
        
        # Create some module files
        with open(os.path.join(pkg_dir, "core.py"), "wb") as f:
            # File size will be roughly size_per_package KB
            f.write(b"x" * (size_per_package * 1024))


def _add_git_repo(venv_path, has_uncommitted_changes):
    """Add a fake git repository to the venv."""
    git_dir = os.path.join(venv_path, ".git")
    os.makedirs(git_dir, exist_ok=True)
    
    # Create basic git structure
    os.makedirs(os.path.join(git_dir, "refs", "heads"), exist_ok=True)
    os.makedirs(os.path.join(git_dir, "objects"), exist_ok=True)
    
    # Create HEAD file
    with open(os.path.join(git_dir, "HEAD"), "w") as f:
        f.write("ref: refs/heads/main\n")
    
    # Create config file
    with open(os.path.join(git_dir, "config"), "w") as f:
        f.write("[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n")
    
    # Create index file (simulate uncommitted changes)
    if has_uncommitted_changes:
        with open(os.path.join(git_dir, "index"), "wb") as f:
            f.write(b"\x00" * 100)


def _corrupt_venv(venv_path, corruption_type):
    """Corrupt the venv in a specific way."""
    if corruption_type == "missing_python":
        # Remove python executable
        if os.name == "nt":
            os.remove(os.path.join(venv_path, "Scripts", "python.exe"))
        else:
            os.remove(os.path.join(venv_path, "bin", "python"))
    
    elif corruption_type == "missing_activate":
        # Remove activate script
        if os.name == "nt":
            os.remove(os.path.join(venv_path, "Scripts", "activate.bat"))
        else:
            os.remove(os.path.join(venv_path, "bin", "activate"))
    
    elif corruption_type == "incomplete_dirs":
        # Remove lib directory
        if os.name == "nt":
            shutil.rmtree(os.path.join(venv_path, "Lib"))
        else:
            shutil.rmtree(os.path.join(venv_path, "lib"))


def simulate_venv_activity(venv_path, activity_pattern="regular", days=30):
    """
    Simulate activity patterns on a venv by modifying file timestamps.
    
    Args:
        venv_path: Path to the venv
        activity_pattern: Type of activity pattern 
                          ("regular", "sporadic", "recent_only", "abandoned")
        days: Number of days to simulate activity for
    """
    # Determine the bin directory based on OS
    if os.name == "nt":
        bin_dir = os.path.join(venv_path, "Scripts")
        activate_script = os.path.join(bin_dir, "activate.bat")
        python_exe = os.path.join(bin_dir, "python.exe")
        pip_exe = os.path.join(bin_dir, "pip.exe")
    else:
        bin_dir = os.path.join(venv_path, "bin")
        activate_script = os.path.join(bin_dir, "activate")
        python_exe = os.path.join(bin_dir, "python")
        pip_exe = os.path.join(bin_dir, "pip")
    
    # Get current time
    now = datetime.now()
    
    if activity_pattern == "regular":
        # Regular activity every few days
        for day in range(days, 0, -5):  # Every 5 days
            access_time = now - timedelta(days=day)
            timestamp = access_time.timestamp()
            
            # Update activate script and python exe
            try:
                os.utime(activate_script, (timestamp, timestamp))
                os.utime(python_exe, (timestamp, timestamp))
            except FileNotFoundError:
                pass
    
    elif activity_pattern == "sporadic":
        # Sporadic activity with gaps
        activity_days = [days - i for i in [1, 5, 15, 16, 29]]  # Random days
        for day in activity_days:
            if day > 0:
                access_time = now - timedelta(days=day)
                timestamp = access_time.timestamp()
                
                # Update files
                try:
                    os.utime(activate_script, (timestamp, timestamp))
                except FileNotFoundError:
                    pass
    
    elif activity_pattern == "recent_only":
        # Only recent activity
        recent_time = now - timedelta(days=2)
        old_time = now - timedelta(days=days)
        
        # Set old time for most files
        for root, dirs, files in os.walk(venv_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.utime(file_path, (old_time.timestamp(), old_time.timestamp()))
                except (FileNotFoundError, PermissionError):
                    pass
        
        # Set recent time for activation scripts
        try:
            os.utime(activate_script, (recent_time.timestamp(), old_time.timestamp()))
            os.utime(python_exe, (recent_time.timestamp(), old_time.timestamp()))
        except FileNotFoundError:
            pass
    
    elif activity_pattern == "abandoned":
        # No recent activity at all
        old_time = now - timedelta(days=days)
        timestamp = old_time.timestamp()
        
        # Set old time for all files
        for root, dirs, files in os.walk(venv_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.utime(file_path, (timestamp, timestamp))
                except (FileNotFoundError, PermissionError):
                    pass


def create_mixed_venv_environment(base_dir, count=10):
    """
    Create a mixed environment with various venvs for realistic testing.
    
    Args:
        base_dir: Base directory to create venvs in
        count: Number of venvs to create
        
    Returns:
        Dictionary with details of created venvs
    """
    import random
    
    venv_patterns = [
        # name, age range, active, size range KB, activity pattern
        ("project", (30, 120), False, (1000, 5000), "abandoned"),
        ("api", (15, 45), True, (2000, 8000), "regular"),
        ("webapp", (5, 60), True, (5000, 15000), "recent_only"),
        ("test", (1, 10), False, (500, 2000), "sporadic"),
        ("legacy", (180, 365), False, (3000, 10000), "abandoned"),
        ("temp", (1, 5), False, (100, 500), "recent_only"),
    ]
    
    results = {}
    
    for i in range(count):
        # Randomly select a pattern
        pattern = random.choice(venv_patterns)
        name_base, age_range, is_active, size_range, activity = pattern
        
        # Generate random values
        name = f"{name_base}-{i+1}"
        age = random.randint(age_range[0], age_range[1])
        size = random.randint(size_range[0], size_range[1])
        
        # Create venv
        venv_path = os.path.join(base_dir, name)
        _create_basic_venv_structure(venv_path, age, is_active)
        
        # Create some fake packages to reach desired size
        packages = ["pkg1", "pkg2", "pkg3"]
        _add_packages_to_venv(venv_path, packages, size // len(packages))
        
        # Simulate activity pattern
        simulate_venv_activity(venv_path, activity, age)
        
        # Record details
        results[name] = {
            "path": venv_path,
            "age_days": age,
            "is_active": is_active,
            "size_kb": size,
            "activity_pattern": activity
        }
    
    return results