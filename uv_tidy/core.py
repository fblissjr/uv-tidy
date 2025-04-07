# uv_tidy/core.py
import os
import shutil
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

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

def find_venvs(base_dir: str, max_depth: int = 10, exclude_dirs: List[str] = None) -> List[str]:
    """
    Find all uv venvs in the given directory (recursively).
    
    Args:
        base_dir: Directory to search for venvs
        max_depth: Maximum recursion depth to prevent excessive scanning
        exclude_dirs: Directories to exclude from scanning (e.g., ".git", "node_modules")
        
    Returns:
        List of paths to venvs
    """
    venvs = []
    
    if exclude_dirs is None:
        exclude_dirs = [".git", "node_modules", "__pycache__", ".pytest_cache", ".vscode", ".idea"]
    
    if not os.path.exists(base_dir):
        logger.warning("directory_not_found", path=base_dir)
        return venvs
    
    if max_depth <= 0:
        logger.debug("max_depth_reached", path=base_dir)
        return venvs
    
    try:
        # First check if this directory itself is a uv venv (for direct matches)
        if is_uv_venv(base_dir):
            venvs.append(base_dir)
            # Don't scan inside venvs (they might have bin/lib dirs that look like venvs)
            return venvs
        
        # Check for .uv directory which often contains venvs
        uv_dir = os.path.join(base_dir, ".uv")
        uv_venvs_dir = os.path.join(uv_dir, "venvs")
        
        # If there's a .uv/venvs directory, check it explicitly as it's a common uv location
        if os.path.isdir(uv_venvs_dir):
            logger.debug("found_uv_venvs_dir", path=uv_venvs_dir)
            for item in os.listdir(uv_venvs_dir):
                full_path = os.path.join(uv_venvs_dir, item)
                if os.path.isdir(full_path) and is_uv_venv(full_path):
                    venvs.append(full_path)
        
        # Recursively scan other directories
        for item in os.listdir(base_dir):
            # Skip excluded directories
            if item in exclude_dirs:
                continue
                
            full_path = os.path.join(base_dir, item)
            
            if os.path.isdir(full_path):
                if is_uv_venv(full_path):
                    venvs.append(full_path)
                else:
                    # Recursively check subdirectories with reduced depth
                    sub_venvs = find_venvs(full_path, max_depth - 1, exclude_dirs)
                    venvs.extend(sub_venvs)
    except PermissionError:
        logger.warning("permission_denied", dir=base_dir)
    except Exception as e:
        logger.warning("error_scanning_directory", dir=base_dir, error=str(e))
    
    return venvs


def is_uv_venv(path: str) -> bool:
    """
    Check if a directory is a uv venv.
    
    Args:
        path: Path to check
        
    Returns:
        True if the directory appears to be a uv venv
    """
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
    if os.path.isfile(os.path.join(path, "pyvenv.cfg")):
        return True
    
    # As a fallback, check for python executable
    python_bin = os.path.join(path, "bin", "python")
    if os.name == "nt":
        python_bin = os.path.join(path, "Scripts", "python.exe")
    
    return os.path.isfile(python_bin)


def evaluate_venv(venv_path: str, criteria: Dict) -> Dict:
    """
    Evaluate a venv against the given criteria to determine if it should be removed.
    
    Args:
        venv_path: Path to the venv
        criteria: Dictionary of criteria to check against
        
    Returns:
        Dictionary with evaluation results
    """
    from uv_tidy.utils import get_dir_size, is_venv_active
    
    now = time.time()
    
    try:
        # Get venv metadata
        last_accessed = os.path.getatime(venv_path)
        last_modified = os.path.getmtime(venv_path)
        creation_time = os.path.getctime(venv_path)
        size_bytes = get_dir_size(venv_path)
        
        age_days = (now - last_accessed) / (60 * 60 * 24)
        is_active = is_venv_active(venv_path)
        
        # Initialize result
        result = {
            "path": venv_path,
            "name": os.path.basename(venv_path),
            "last_accessed": datetime.fromtimestamp(last_accessed).strftime("%Y-%m-%d %H:%M:%S"),
            "last_modified": datetime.fromtimestamp(last_modified).strftime("%Y-%m-%d %H:%M:%S"),
            "created": datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d %H:%M:%S"),
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "age_days": round(age_days, 1),
            "is_active": is_active,
            "status": "keep",
            "reason": None,
        }
        
        # Apply criteria
        min_age_days = criteria.get("min_age_days", 0)
        min_size_mb = criteria.get("min_size_mb")
        unused_only = criteria.get("unused_only", False)
        
        reasons = []
        
        # Too young to remove
        if age_days < min_age_days:
            reasons.append(f"age below threshold ({age_days:.1f} < {min_age_days} days)")
        
        # Too small to bother removing
        if min_size_mb and size_bytes < (min_size_mb * 1024 * 1024):
            reasons.append(f"size below threshold ({result['size_mb']:.1f} < {min_size_mb} MB)")
        
        # Active venv and we only want to remove unused ones
        if unused_only and is_active:
            reasons.append("venv appears to be active")
        
        # If we have reasons to keep, join them and return
        if reasons:
            result["reason"] = "; ".join(reasons)
            return result
        
        # No reasons to keep - this venv should be removed
        result["status"] = "remove"
        result["reason"] = f"unused for {age_days:.1f} days"
        
        # Add more detailed reason if appropriate
        if size_bytes > 100 * 1024 * 1024:  # Larger than 100MB
            result["reason"] += f", size: {result['size_mb']:.1f} MB"
        
        return result
    
    except Exception as e:
        logger.exception("error_evaluating_venv", path=venv_path, error=str(e))
        return {
            "path": venv_path,
            "name": os.path.basename(venv_path),
            "status": "error",
            "reason": f"evaluation error: {str(e)}",
        }


def remove_venv(venv_path: str) -> bool:
    """
    Actually remove a venv directory.
    
    Args:
        venv_path: Path to the venv to remove
        
    Returns:
        True if removal was successful
    """
    try:
        shutil.rmtree(venv_path)
        return True
    except Exception as e:
        logger.exception("error_removing_venv", path=venv_path, error=str(e))
        return False


def summarize_venvs(venv_records: List[Dict]) -> Dict:
    """
    Generate summary statistics for a list of venv records.
    
    Args:
        venv_records: List of venv evaluation records
        
    Returns:
        Dictionary with summary statistics
    """
    to_remove = [r for r in venv_records if r["status"] == "remove"]
    to_keep = [r for r in venv_records if r["status"] == "keep"]
    errors = [r for r in venv_records if r["status"] == "error"]
    
    total_size_to_remove = sum(r.get("size_bytes", 0) for r in to_remove)
    oldest_venv = None
    newest_venv = None
    
    if to_remove:
        # Find oldest and newest venvs based on creation time
        # This is more meaningful than last accessed time
        oldest_idx = 0
        newest_idx = 0
        
        for i, record in enumerate(to_remove):
            if "created" not in record:
                continue
                
            if i == 0:
                oldest_idx = newest_idx = i
                continue
                
            if record["created"] < to_remove[oldest_idx]["created"]:
                oldest_idx = i
            if record["created"] > to_remove[newest_idx]["created"]:
                newest_idx = i
        
        oldest_venv = to_remove[oldest_idx] if oldest_idx < len(to_remove) else None
        newest_venv = to_remove[newest_idx] if newest_idx < len(to_remove) else None
    
    return {
        "total_venvs": len(venv_records),
        "to_remove": len(to_remove),
        "to_keep": len(to_keep),
        "errors": len(errors),
        "total_size_to_remove_bytes": total_size_to_remove,
        "total_size_to_remove_mb": round(total_size_to_remove / (1024 * 1024), 2),
        "oldest_venv": oldest_venv,
        "newest_venv": newest_venv,
    }