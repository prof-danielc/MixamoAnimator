"""Tests for the main entry point of MixamoAnimator."""

import sys
from unittest.mock import patch
import pytest
from main import parse_args


def test_parse_args_success():
    """Test that parse_args correctly parses model_name and animation_name."""
    test_args = ["main.py", "--model_name", "model.fbx", "--animation_name", "dance.fbx"]
    with patch.object(sys, 'argv', test_args):
        args = parse_args()
        assert args.model_name == "model.fbx"
        assert args.animation_name == "dance.fbx"


def test_parse_args_missing_required():
    """Test that parse_args exits when required arguments are missing."""
    test_args = ["main.py"]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit):
            parse_args()
