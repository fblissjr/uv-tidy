# uv_tidy/utils.py
import os
import sys
import time
import platform
from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger()

def is_uv_venv(path: str) -> bool:
    """
    Check if a directory is a uv venv.
    
    Args:
        path: Path to check
        
    Returns:
        True if the directory appears to be a uv venv
    """
    try:
        # Skip non-directories immediately
        if not os.path.isdir(path):
            return False
            
        # A uv venv typically has these subdirectories
        required_dirs = ["bin", "lib", "include"]
        if os.name == "nt":  # Windows
            required_dirs = ["Scripts", "Lib", "Include"]
        
        # Check if required directories exist
        found_dirs = 0
        for req_dir in required_dirs:
            if os.path.isdir(os.path.join(path, req_dir)):
                found_dirs += 1
        
        # Consider it a venv if at least 2 of the 3 required dirs exist
        # This makes the detection more resilient to slightly different venv structures
        if found_dirs < 2:
            return False
        
        # Look for pyvenv.cfg which is typically in venvs
        pyvenv_cfg = os.path.join(path, "pyvenv.cfg")
        if os.path.isfile(pyvenv_cfg):
            # Read the pyvenv.cfg to check for uv-specific markers
            # This helps distinguish uv venvs from other types
            try:
                with open(pyvenv_cfg, 'r') as f:
                    content = f.read()
                    # Check for uv-specific markers in the config
                    # uv often adds a comment or marker in the config
                    if "uv" in content.lower():
                        return True
            except (IOError, UnicodeDecodeError):
                # If we can't read the file, fall back to other checks
                pass
        
        # Check for python executable
        python_bin = os.path.join(path, "bin", "python")
        if os.name == "nt":
            python_bin = os.path.join(path, "Scripts", "python.exe")
        
        has_python = os.path.isfile(python_bin)
        
        # Check for uv-specific markers - look for .uv-proj file which uv often creates
        uv_proj_file = os.path.join(path, ".uv-proj")
        has_uv_marker = os.path.isfile(uv_proj_file)
        
        # If we have Python executable and either a uv marker or pyvenv.cfg
        if has_python and (has_uv_marker or os.path.isfile(pyvenv_cfg)):
            return True
            
        # As a more permissive fallback, if it has the Python executable and 
        # the directory structure, consider it a potentially deletable venv
        if has_python and found_dirs >= 2:
            return True
            
        return False
    except Exception as e:
        # Be safe and don't identify as venv if we encounter any errors
        logger.debug("error_checking_venv", path=path, error=str(e))
        return False
    
def get_dir_size(path: str) -> int:
    """
    Calculate the total size of a directory in bytes.
    
    Args:
        path: Path to directory
        
    Returns:
        Size in bytes
    """
    total_size = 0
    
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except (FileNotFoundError, PermissionError):
                    pass
    except PermissionError:
        logger.warning("permission_denied_during_size_calc", dir=path)
    
    return total_size


def is_venv_active(venv_path: str) -> bool:
    """
    Check if a venv appears to be in use.
    
    This is an approximation and might have false positives/negatives.
    
    Args:
        path: Path to venv
        
    Returns:
        True if the venv appears to be active
    """
    # Strategy 1: Check for recent access of activation scripts
    activate_scripts = []
    
    if platform.system() == "Windows":
        activate_scripts = [
            os.path.join(venv_path, "Scripts", "activate.bat"),
            os.path.join(venv_path, "Scripts", "activate.ps1"),
        ]
    else:
        activate_scripts = [
            os.path.join(venv_path, "bin", "activate"),
            os.path.join(venv_path, "bin", "activate.fish"),
            os.path.join(venv_path, "bin", "activate.csh"),
        ]
    
    now = time.time()
    for script in activate_scripts:
        if os.path.exists(script):
            try:
                last_accessed = os.path.getatime(script)
                hours_since_activation = (now - last_accessed) / 3600
                
                # If activated in the last 24 hours, consider it active
                if hours_since_activation < 24:
                    return True
            except OSError:
                pass
    
    # Strategy 2: Check for recent pip or pip-related file access
    pip_exes = []
    
    if platform.system() == "Windows":
        pip_exes = [
            os.path.join(venv_path, "Scripts", "pip.exe"),
            os.path.join(venv_path, "Scripts", "pip3.exe"),
            os.path.join(venv_path, "Scripts", "pip-script.py"),
        ]
    else:
        pip_exes = [
            os.path.join(venv_path, "bin", "pip"),
            os.path.join(venv_path, "bin", "pip3"),
        ]
    
    for pip_exe in pip_exes:
        if os.path.exists(pip_exe):
            try:
                last_accessed = os.path.getatime(pip_exe)
                days_since_pip_use = (now - last_accessed) / (24 * 3600)
                
                # If pip was used in the last 7 days, consider it active
                if days_since_pip_use < 7:
                    return True
            except OSError:
                pass
    
    # Strategy 3: Try to find a .project file
    # Sometimes IDEs or tools leave project markers
    project_markers = [".project", ".vscode", ".idea"]
    for marker in project_markers:
        marker_path = os.path.join(venv_path, marker)
        if os.path.exists(marker_path):
            # If the marker was modified in the last 30 days, consider it active
            try:
                last_modified = os.path.getmtime(marker_path)
                days_since_modified = (now - last_modified) / (24 * 3600)
                if days_since_modified < 30:
                    return True
            except OSError:
                pass
    
    return False


def get_default_venv_dirs() -> List[str]:
    """
    Return default directories where uv stores venvs based on OS.
    
    Returns:
        List of default venv directories
    """
    home = os.path.expanduser("~")
    
    # Add common project directories where venvs might be created
    project_dirs = [
        os.path.join(home, "projects"),
        os.path.join(home, "dev"),
        os.path.join(home, "code"),
        os.path.join(home, "workspace"),
    ]
    
    # Filter to only include directories that exist
    project_dirs = [d for d in project_dirs if os.path.isdir(d)]
    
    # Add OS-specific uv directories
    uv_dirs = []
    
    if platform.system() == "Darwin":  # macOS
        uv_dirs = [
            os.path.join(home, ".uv", "venvs"),
            os.path.join(home, ".local", "share", "uv", "venvs"),
            os.path.join(home, "Library", "Caches", "uv", "venvs"),
        ]
    elif platform.system() == "Linux":
        uv_dirs = [
            os.path.join(home, ".uv", "venvs"),
            os.path.join(home, ".local", "share", "uv", "venvs"),
            os.path.join(home, ".cache", "uv", "venvs"),
        ]
    elif platform.system() == "Windows":
        appdata = os.environ.get("LOCALAPPDATA", "")
        uv_dirs = [
            os.path.join(home, ".uv", "venvs"),
            os.path.join(appdata, "uv", "venvs") if appdata else "",
        ]
    else:
        logger.warning("unsupported_platform", platform=platform.system())
        uv_dirs = [os.path.join(home, ".uv", "venvs")]
    
    # Return uv-specific directories first (more likely to contain venvs)
    # and then general project directories (might require deeper scanning)
    return [d for d in uv_dirs if d and os.path.exists(d)] + project_dirs


def filter_paths(paths: List[str], exclude_patterns: List[str]) -> List[str]:
    """
    Filter out paths matching any of the exclude patterns.
    
    Args:
        paths: List of paths to filter
        exclude_patterns: List of patterns to exclude
        
    Returns:
        Filtered list of paths
    """
    import fnmatch
    
    if not exclude_patterns:
        return paths
    
    filtered = []
    for path in paths:
        skip = False
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(path, pattern):
                skip = True
                break
        
        if not skip:
            filtered.append(path)
    
    return filtered


def format_size(size_bytes: int) -> str:
    """
    Format a size in bytes to a human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"