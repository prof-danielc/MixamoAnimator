import pytest
from unittest.mock import MagicMock, patch
from cli.ui import UI

def test_ui_display_api_status():
    ui = UI()
    with patch.object(ui.console, "print") as mock_print:
        ui.display_api_status(True)
        mock_print.assert_called_once()
        args = mock_print.call_args[0][0]
        assert "Active" in args
        
        mock_print.reset_mock()
        ui.display_api_status(False)
        mock_print.assert_called_once()
        args = mock_print.call_args[0][0]
        assert "Inactive" in args

def test_ui_create_progress_bar():
    ui = UI()
    progress = ui.create_progress_bar()
    assert progress is not None
    # Check if TimeRemainingColumn was added
    assert any(isinstance(col, (pytest.importorskip("rich.progress").TimeRemainingColumn)) for col in progress.columns)
