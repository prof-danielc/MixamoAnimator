import pytest
from main import create_parser

def test_inplace_flag_presence():
    parser = create_parser()
    # Check if --inplace is in the parser (expect failure initially because it's not added yet)
    args = parser.parse_args(["--inplace", "--model_path", "test.fbx"])
    assert args.inplace is True

def test_inplace_flag_default_false():
    parser = create_parser()
    args = parser.parse_args(["--model_path", "test.fbx"])
    assert args.inplace is False
