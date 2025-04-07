# uv_tidy/cli.py
import argparse
import os
import sys
import time
from typing import Dict, List, Optional

import structlog

from uv_tidy.core import find_venvs, evaluate_venv, remove_venv, summarize_venvs
from uv_tidy.utils import get_default_venv_dirs, filter_paths, format_size
from uv_tidy.rules import make_criteria, sort_venvs_by_criteria, prune_candidates


def setup_logging(verbose: bool, format_output: str = "console") -> None:
    """
    Set up structlog logger.
    
    Args:
        verbose: Whether to enable verbose logging
        format_output: Output format (console, json)
    """
    log_level = "DEBUG" if verbose else "INFO"
    
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if format_output == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="uv-tidy: Clean up unused uv virtual environments"
    )
    
    # Directory selection options
    parser.add_argument(
        "--venv-dir", 
        help="path to directory containing uv venvs (defaults to standard locations)"
    )
    parser.add_argument(
        "--exclude", 
        action="append", 
        help="exclude paths matching this pattern (can be used multiple times)"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=10,
        help="maximum recursion depth when scanning directories (default: 10)"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="disable recursive scanning of subdirectories"
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        help="exclude these directory names when scanning (can be used multiple times)"
    )
    
    # Filtering criteria
    parser.add_argument(
        "--min-age-days", 
        type=int, 
        default=30, 
        help="minimum age in days to consider a venv unused (default: 30)"
    )
    parser.add_argument(
        "--min-size-mb", 
        type=int, 
        help="minimum size in MB to consider removing a venv"
    )
    parser.add_argument(
        "--unused-only", 
        action="store_true", 
        default=True,
        help="only consider venvs that appear unused (default: True)"
    )
    parser.add_argument(
        "--sort-by",
        choices=["age", "size", "name", "accessed", "modified", "created"],
        default="age",
        help="sort venvs by this criterion (default: age)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="limit the number of venvs to remove"
    )
    
    # Execution options
    parser.add_argument(
        "--yes",
        action="store_true",
        help="apply changes without prompting (default is dry-run)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="output logs in JSON format",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="enable verbose logging",
    )
    
    return parser.parse_args()


def main() -> None:
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Setup logging
    format_output = "json" if args.json else "console"
    setup_logging(args.verbose, format_output)
    
    logger = structlog.get_logger()
    logger.info("uv_tidy_started", version="0.1.0")
    
    # Determine venv directories to scan
    venv_dirs = [args.venv_dir] if args.venv_dir else get_default_venv_dirs()
    venv_dirs = [d for d in venv_dirs if d and os.path.exists(d)]
    
    if not venv_dirs:
        logger.error("no_valid_venv_dirs_found")
        sys.exit(1)
    
    logger.info("scanning_directories", dirs=venv_dirs)
    
    # Find all venvs
    all_venvs = []
    
    # Extract exclude_dirs from args
    exclude_dirs = args.exclude_dir or [".git", "node_modules", "__pycache__", ".pytest_cache"]
    
    # Set max_depth based on args
    max_depth = 1 if args.no_recursive else args.max_depth
    
    # Find venvs in each directory
    for venv_dir in venv_dirs:
        logger.info("scanning", dir=venv_dir, recursive=not args.no_recursive, max_depth=max_depth)
        venvs = find_venvs(venv_dir, max_depth=max_depth, exclude_dirs=exclude_dirs)
        logger.info("found_venvs", dir=venv_dir, count=len(venvs))
        all_venvs.extend(venvs)
    
    if not all_venvs:
        logger.info("no_venvs_found")
        return
    
    # Filter out excluded paths
    if args.exclude:
        all_venvs = filter_paths(all_venvs, args.exclude)
        logger.info("after_exclusions", count=len(all_venvs))
    
    # Make criteria from command-line args
    criteria = make_criteria(vars(args))
    logger.info("using_criteria", **criteria)
    
    # Evaluate each venv
    venv_records = []
    start_time = time.time()
    for venv in all_venvs:
        record = evaluate_venv(venv, criteria)
        venv_records.append(record)
    
    eval_time = time.time() - start_time
    logger.debug("evaluation_complete", time_seconds=round(eval_time, 2))
    
    # Sort venvs
    venv_records = sort_venvs_by_criteria(venv_records, args.sort_by)
    
    # Generate summary
    summary = summarize_venvs(venv_records)
    
    # Limit the number to remove if requested
    if args.limit is not None:
        to_remove = prune_candidates(venv_records, args.limit)
    else:
        to_remove = [r for r in venv_records if r["status"] == "remove"]
    
    # Output summary
    if not to_remove:
        logger.info("no_venvs_to_remove", total_found=len(venv_records))
        return
    
    total_size = sum(r.get("size_bytes", 0) for r in to_remove)
    logger.info(
        "dry_run_summary",
        venvs_to_remove=len(to_remove),
        total_size=format_size(total_size),
    )
    
    # Show what would be removed
    for record in to_remove:
        logger.info(
            "venv_to_remove",
            path=record["path"],
            size=format_size(record.get("size_bytes", 0)),
            age_days=record.get("age_days", "unknown"),
            reason=record.get("reason", "unknown"),
        )
    
    # Ask for confirmation if not --yes
    if not args.yes:
        if sys.stdin.isatty():
            try:
                confirm = input("\nContinue and remove these venvs? [y/N]: ").strip().lower()
                if confirm not in ("y", "yes"):
                    logger.info("operation_aborted")
                    return
            except (KeyboardInterrupt, EOFError):
                print()  # Add newline after ^C
                logger.info("operation_aborted")
                return
        else:
            logger.error("confirmation_required_in_non_interactive_mode")
            sys.exit(1)
    
    # Actually remove the venvs
    removed = 0
    total_removed_bytes = 0
    for record in to_remove:
        size_bytes = record.get("size_bytes", 0)
        success = remove_venv(record["path"])
        if success:
            logger.info(
                "venv_removed", 
                path=record["path"], 
                size=format_size(size_bytes)
            )
            removed += 1
            total_removed_bytes += size_bytes
        else:
            logger.error("failed_to_remove_venv", path=record["path"])
    
    # Final summary
    logger.info(
        "operation_complete", 
        venvs_removed=removed, 
        total_size_freed=format_size(total_removed_bytes)
    )


if __name__ == "__main__":
    main()