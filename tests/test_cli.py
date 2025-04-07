# tests/test_cli.py
import os
import sys
import subprocess
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from uv_tidy.cli import parse_args, main, setup_logging


def test_setup_logging():
    """Test logging setup with different options."""
    # Just making sure it doesn't crash
    setup_logging(verbose=False)
    setup_logging(verbose=True)
    setup_logging(verbose=False, format_output="json")


def test_parse_args():
    """Test argument parsing."""
    # Test with minimal args
    with patch('sys.argv', ['uv-tidy']):
        args = parse_args()
        assert args.min_age_days == 30, "Default min_age_days should be 30"
        assert args.unused_only == True, "Default unused_only should be True"
        assert args.venv_dir is None, "Default venv_dir should be None"
        assert args.yes is False, "Default yes should be False"
    
    # Test with custom args
    with patch('sys.argv', [
        'uv-tidy',
        '--min-age-days', '60',
        '--min-size-mb', '50',
        '--venv-dir', '/custom/path',
        '--yes',
        '--verbose'
    ]):
        args = parse_args()
        assert args.min_age_days == 60, "Wrong min_age_days"
        assert args.min_size_mb == 50, "Wrong min_size_mb"
        assert args.venv_dir == '/custom/path', "Wrong venv_dir"
        assert args.yes is True, "Wrong yes value"
        assert args.verbose is True, "Wrong verbose value"
    
    # Test with exclude patterns
    with patch('sys.argv', [
        'uv-tidy',
        '--exclude', '*test*',
        '--exclude', '*dev*'
    ]):
        args = parse_args()
        assert len(args.exclude) == 2, "Wrong number of exclude patterns"
        assert '*test*' in args.exclude, "Missing exclude pattern"
        assert '*dev*' in args.exclude, "Missing exclude pattern"


@patch('uv_tidy.cli.find_venvs')
@patch('uv_tidy.cli.evaluate_venv')
@patch('uv_tidy.cli.get_default_venv_dirs')
@patch('uv_tidy.cli.remove_venv')
@patch('builtins.input', return_value='y')
def test_main_workflow(mock_input, mock_remove, mock_get_dirs, mock_evaluate, mock_find, temp_dir):
    """Test the main workflow."""
    # Setup mocks
    mock_get_dirs.return_value = [temp_dir]
    mock_find.return_value = [os.path.join(temp_dir, 'venv1'), os.path.join(temp_dir, 'venv2')]
    
    # Mock evaluations
    mock_evaluate.side_effect = [
        # venv1: old and inactive
        {
            "path": os.path.join(temp_dir, 'venv1'),
            "name": "venv1",
            "age_days": 45,
            "size_bytes": 10485760,  # 10MB
            "is_active": False,
            "status": "remove",
            "reason": "unused for 45 days",
        },
        # venv2: recent and active
        {
            "path": os.path.join(temp_dir, 'venv2'),
            "name": "venv2",
            "age_days": 5,
            "size_bytes": 5242880,  # 5MB
            "is_active": True,
            "status": "keep",
            "reason": "venv appears to be active",
        }
    ]
    
    # Mock successful removal
    mock_remove.return_value = True
    
    # Run with --yes flag
    with patch('sys.argv', ['uv-tidy', '--yes']):
        main()
    
    # Verify the workflow
    mock_get_dirs.assert_called_once()
    mock_find.assert_called_once()
    assert mock_evaluate.call_count == 2, "evaluate_venv should be called for each venv"
    
    # Only venv1 should be removed
    mock_remove.assert_called_once_with(os.path.join(temp_dir, 'venv1'))


@patch('uv_tidy.cli.find_venvs')
@patch('uv_tidy.cli.get_default_venv_dirs')
def test_main_no_venvs(mock_get_dirs, mock_find, temp_dir):
    """Test main when no venvs are found."""
    # Setup mocks
    mock_get_dirs.return_value = [temp_dir]
    mock_find.return_value = []
    
    # Run with empty result
    with patch('sys.argv', ['uv-tidy']):
        main()
    
    # Verify the workflow stops early
    mock_get_dirs.assert_called_once()
    mock_find.assert_called_once()


@patch('uv_tidy.cli.find_venvs')
@patch('uv_tidy.cli.evaluate_venv')
@patch('uv_tidy.cli.get_default_venv_dirs')
@patch('builtins.input', return_value='n')
def test_main_abort_on_no(mock_input, mock_get_dirs, mock_evaluate, mock_find, temp_dir):
    """Test aborting when user answers 'n' to the confirmation."""
    # Setup mocks
    mock_get_dirs.return_value = [temp_dir]
    mock_find.return_value = [os.path.join(temp_dir, 'venv1')]
    
    # Mock evaluations
    mock_evaluate.return_value = {
        "path": os.path.join(temp_dir, 'venv1'),
        "name": "venv1",
        "status": "remove",
    }
    
    # Patch sys.stdin.isatty to return True (simulate interactive mode)
    with patch('sys.stdin.isatty', return_value=True):
        # Run without --yes flag
        with patch('sys.argv', ['uv-tidy']):
            main()
    
    # User answered "n", so removal should not happen
    mock_input.assert_called_once()


@patch('uv_tidy.cli.find_venvs')
@patch('uv_tidy.cli.evaluate_venv')
@patch('uv_tidy.cli.get_default_venv_dirs')
def test_main_noninteractive_without_yes(mock_get_dirs, mock_evaluate, mock_find, temp_dir):
    """Test running in non-interactive mode without --yes flag."""
    # Setup mocks
    mock_get_dirs.return_value = [temp_dir]
    mock_find.return_value = [os.path.join(temp_dir, 'venv1')]
    
    # Mock evaluations
    mock_evaluate.return_value = {
        "path": os.path.join(temp_dir, 'venv1'),
        "name": "venv1",
        "status": "remove",
    }
    
    # Patch sys.stdin.isatty to return False (simulate non-interactive mode)
    with patch('sys.stdin.isatty', return_value=False):
        # Run without --yes flag
        with patch('sys.argv', ['uv-tidy']):
            # Should exit with error
            with pytest.raises(SystemExit) as excinfo:
                main()
            assert excinfo.value.code == 1, "Expected exit code 1"