# uv_tidy/rules.py
import os
import time
from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger()


def make_criteria(args: Dict) -> Dict:
    """
    Create a criteria dictionary from command-line arguments.
    
    Args:
        args: Dictionary of command-line arguments
        
    Returns:
        Dictionary of criteria
    """
    criteria = {
        "min_age_days": args.get("min_age_days", 30),
        "unused_only": args.get("unused_only", True),
    }
    
    # Only include size criterion if specified
    if args.get("min_size_mb") is not None:
        criteria["min_size_mb"] = args["min_size_mb"]
    
    return criteria


def sort_venvs_by_criteria(venvs: List[Dict], sort_by: str) -> List[Dict]:
    """
    Sort venvs by the specified criterion.
    
    Args:
        venvs: List of venv dictionaries
        sort_by: Criterion to sort by (age, size, name, accessed)
        
    Returns:
        Sorted list of venvs
    """
    if not venvs:
        return []
    
    valid_sort_keys = {
        "age": "age_days",
        "size": "size_bytes",
        "name": "name",
        "accessed": "last_accessed",
        "modified": "last_modified",
        "created": "created"
    }
    
    sort_key = valid_sort_keys.get(sort_by.lower(), "age_days")
    reverse = sort_key != "name"  # Sort descending except for name
    
    # Make a copy to avoid modifying the original
    sorted_venvs = list(venvs)
    
    # Handle missing keys gracefully
    def safe_sort_key(venv):
        if sort_key in venv:
            return venv[sort_key]
        # Provide default values based on the sort key
        if sort_key == "age_days":
            return 0
        elif sort_key == "size_bytes":
            return 0
        elif sort_key in ("last_accessed", "last_modified", "created"):
            return ""
        else:
            return venv.get("name", "")
    
    return sorted(sorted_venvs, key=safe_sort_key, reverse=reverse)


def prune_candidates(venvs: List[Dict], limit: int = None) -> List[Dict]:
    """
    Limit the number of venvs to remove if specified.
    
    Args:
        venvs: List of venv dictionaries
        limit: Maximum number of venvs to remove (None = no limit)
        
    Returns:
        Pruned list of venvs
    """
    to_remove = [v for v in venvs if v["status"] == "remove"]
    
    if limit is not None and len(to_remove) > limit:
        logger.info("limiting_removal", original=len(to_remove), limit=limit)
        return to_remove[:limit]
    
    return to_remove


def auto_adjust_criteria(venvs: List[Dict], target_count: int) -> Dict:
    """
    Automatically adjust criteria to target a specific number of venvs to remove.
    
    This is useful for "I want to remove about X venvs" scenarios.
    
    Args:
        venvs: List of venv dictionaries (must include size_bytes and age_days)
        target_count: Target number of venvs to remove
        
    Returns:
        Adjusted criteria dictionary
    """
    if not venvs or target_count <= 0 or target_count >= len(venvs):
        return {"min_age_days": 7, "unused_only": True}
    
    # Sort by age (oldest first)
    sorted_by_age = sorted(venvs, key=lambda v: v.get("age_days", 0), reverse=True)
    
    # Find the age threshold that would give us approximately target_count venvs
    threshold_idx = min(target_count, len(sorted_by_age) - 1)
    threshold_age = sorted_by_age[threshold_idx].get("age_days", 7)
    
    # Round to a reasonable number (at least 7 days)
    threshold_age = max(7, int(threshold_age))
    
    return {
        "min_age_days": threshold_age,
        "unused_only": True,
    }