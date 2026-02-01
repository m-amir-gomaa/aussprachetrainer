
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Create a stub for CTkFrame
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

class TestUmlautInput(unittest.TestCase):
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

    def test_umlaut_insertion(self):
        self.mock_zep_instance.get_mode.return_value = "INSERT"
        test_cases = [
            ("a", "ä"), ("A", "Ä"),
            ("o", "ö"), ("O", "Ö"),
            ("u", "ü"), ("U", "Ü"),
        ]
        for key, expected in test_cases:
            event = MagicMock()
            event.keysym = key
            event.state = 0x8 # Alt
            self.mock_zep_instance.handle_key.reset_mock()
            self.editor._on_key_press(event)
            self.mock_zep_instance.handle_key.assert_called_with(expected, 0)

    def test_eszett_sequence(self):
        self.mock_zep_instance.get_mode.return_value = "INSERT"
        
        # 1. First Alt+s -> inserts 's'
        event1 = MagicMock()
        event1.keysym = "s"
        event1.state = 0x8
        self.mock_zep_instance.get_text.return_value = ""
        self.mock_zep_instance.get_cursor.return_value = (0, 0)
        
        self.mock_zep_instance.handle_key.reset_mock()
        self.editor._on_key_press(event1)
        self.mock_zep_instance.handle_key.assert_called_with("s", 0)
        
        # 2. Second Alt+s -> replaces with 'ß'
        event2 = MagicMock()
        event2.keysym = "s"
        event2.state = 0x8
        self.mock_zep_instance.get_text.return_value = "s"
        self.mock_zep_instance.get_cursor.return_value = (0, 1)
        
        self.mock_zep_instance.handle_key.reset_mock()
        self.editor._on_key_press(event2)
        
        calls = self.mock_zep_instance.handle_key.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0][0], "BackSpace")
        self.assertEqual(calls[1][0][0], "ß")

    def test_eszett_capital_sequence(self):
        self.mock_zep_instance.get_mode.return_value = "INSERT"
        
        # 1. First Alt+S -> inserts 'S'
        event1 = MagicMock()
        event1.keysym = "S"
        event1.state = 0x9 # Alt + Shift
        self.mock_zep_instance.get_text.return_value = ""
        self.mock_zep_instance.get_cursor.return_value = (0, 0)
        
        self.mock_zep_instance.handle_key.reset_mock()
        self.editor._on_key_press(event1)
        self.mock_zep_instance.handle_key.assert_called_with("S", 0)
        
        # 2. Second Alt+S -> replaces with 'ẞ'
        event2 = MagicMock()
        event2.keysym = "S"
        event2.state = 0x9
        self.mock_zep_instance.get_text.return_value = "S"
        self.mock_zep_instance.get_cursor.return_value = (0, 1)
        
        self.mock_zep_instance.handle_key.reset_mock()
        self.editor._on_key_press(event2)
        
        calls = self.mock_zep_instance.handle_key.call_args_list
        self.assertEqual(calls[0][0][0], "BackSpace")
        self.assertEqual(calls[1][0][0], "ẞ")

    def test_extended_alt_detection(self):
        self.mock_zep_instance.get_mode.return_value = "INSERT"
        event = MagicMock()
        event.keysym = "u"
        event.state = 0x20000 # Extended Alt on some Linux systems
        self.mock_zep_instance.handle_key.reset_mock()
        self.editor._on_key_press(event)
        self.mock_zep_instance.handle_key.assert_called_with("ü", 0)

if __name__ == "__main__":
    unittest.main()
