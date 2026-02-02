
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Stub for CTkFrame
class StubCTkFrame:
    def __init__(self, master=None, **kwargs):
        self.master = master
    def pack(self, **kwargs): pass
    def bind(self, *args): pass
    def quit(self): pass
    def destroy(self): pass
    def winfo_toplevel(self): 
        m = MagicMock()
        m.suggestions = None
        return m
    def winfo_height(self): return 100
    def winfo_width(self): return 100
    def after(self, ms, func): pass

# Mock customtkinter and tkinter
sys.modules["customtkinter"] = MagicMock()
sys.modules["customtkinter"].CTkFrame = StubCTkFrame
sys.modules["tkinter"] = MagicMock()
class StubCanvas:
    def __init__(self, master, **kwargs): pass
    def pack(self, **kwargs): pass
    def bind(self, *args): pass
    def delete(self, *args): pass
    def create_text(self, *args, **kwargs): pass
    def create_rectangle(self, *args, **kwargs): pass
    def focus_set(self): pass
sys.modules["tkinter"].Canvas = StubCanvas
sys.modules["tkinter.font"] = MagicMock()

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from aussprachetrainer.vim_editor import VimEditor

class TestRAndRedo(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("aussprachetrainer.vim_editor.zep_vim")
        self.mock_zep_module = self.patcher.start()
        self.mock_zep_instance = MagicMock()
        self.mock_zep_module.ZepVim.return_value = self.mock_zep_instance
        self.mock_zep_instance.get_cursor.return_value = (0, 0)
        self.mock_zep_instance.get_text.return_value = ""
        self.mock_zep_instance.get_mode.return_value = "NORMAL"
        self.editor = VimEditor(MagicMock())
        self.editor.after = MagicMock() 

    def tearDown(self):
        self.patcher.stop()

    def test_r_command_passed_to_zep(self):
        # 'r' should be handled by Zep
        event = MagicMock()
        event.keysym = "r"
        event.state = 0x0
        self.mock_zep_instance.handle_key.reset_mock()
        self.editor._on_key_press(event)
        self.mock_zep_instance.handle_key.assert_called_with("r", 0x0)

    def test_redo_ctrl_r_passed_to_zep(self):
        # Ctrl+r should now be passed to Zep (not blocked by VimEditor or GUI)
        event = MagicMock()
        event.keysym = "r"
        event.state = 0x4 # Ctrl
        self.mock_zep_instance.handle_key.reset_mock()
        self.editor._on_key_press(event)
        self.mock_zep_instance.handle_key.assert_called_with("r", 0x4)

    def test_global_intercepts_still_work(self):
        # Verify that Ctrl+p is still blocked (so GUI can handle it)
        event = MagicMock()
        event.keysym = "p"
        event.state = 0x4 # Ctrl
        self.mock_zep_instance.handle_key.reset_mock()
        res = self.editor._on_key_press(event)
        self.assertIsNone(res) # Should return None (implied by 'return' in code)
        self.mock_zep_instance.handle_key.assert_not_called()

    def test_alt_r_passthrough(self):
        # Alt+r should be passed through (return None)
        event = MagicMock()
        event.keysym = "r"
        event.state = 0x8 # Alt (Mod1)
        self.mock_zep_instance.handle_key.reset_mock()
        res = self.editor._on_key_press(event)
        self.assertIsNone(res)
        self.mock_zep_instance.handle_key.assert_not_called()

if __name__ == "__main__":
    unittest.main()
