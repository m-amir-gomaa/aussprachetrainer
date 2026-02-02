
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from aussprachetrainer import zep_vim
except ImportError:
    print("zep_vim not found. Make sure it's compiled.")
    sys.exit(1)

# Stub for CTkFrame and other GUI components
class StubCTkFrame:
    def __init__(self, master=None, **kwargs):
        self.master = master
        self._clipboard = ""
    def pack(self, **kwargs): pass
    def bind(self, *args): pass
    def winfo_toplevel(self): 
        m = MagicMock()
        m.suggestions = None
        return m
    def winfo_height(self): return 100
    def winfo_width(self): return 100
    def after(self, ms, func): pass
    def clipboard_get(self): return self._clipboard
    def clipboard_clear(self): self._clipboard = ""
    def clipboard_append(self, text): self._clipboard += text

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

from aussprachetrainer.vim_editor import VimEditor

class TestVimClipboardFull(unittest.TestCase):
    def setUp(self):
        # We want to use the REAL zep_vim module now that it's compiled
        self.editor = VimEditor(MagicMock())
        self.editor.zep = zep_vim.ZepVim()
        self.editor._render_vimbuffer = MagicMock()

    def test_vim_yank_sync_to_system(self):
        self.editor.zep.set_text("hello world")
        # Go to Normal mode (default)
        # Yank the whole line: yy
        event = MagicMock()
        event.keysym = "y"
        event.state = 0
        self.editor._on_key_press(event)
        self.editor._on_key_press(event) # yy
        
        # Check system clipboard (simulated in StubCTkFrame)
        self.assertEqual(self.editor.clipboard_get(), "hello world\n")

    def test_vim_paste_sync_from_system(self):
        self.editor.zep.set_text("hello")
        # Go to end of line: $
        self.editor.zep.handle_key("$", 0) 
        
        # Put something in system clipboard
        self.editor.clipboard_clear()
        self.editor.clipboard_append(" world")
        
        # Press 'p' in Normal mode (paste after cursor)
        event = MagicMock()
        event.keysym = "p"
        event.state = 0
        self.editor._on_key_press(event)
        
        self.assertEqual(self.editor.zep.get_text(), "hello world")

    def test_gui_ctrl_a_ctrl_c(self):
        self.editor.zep.set_text("select me")
        
        # Ctrl+A
        event = MagicMock()
        event.keysym = "a"
        event.state = 0x4 # Ctrl
        self.editor._on_key_press(event)
        
        self.assertEqual(self.editor.zep.get_mode(), "VISUAL")
        
        # Ctrl+C
        event.keysym = "c"
        self.editor._on_key_press(event)
        
        self.assertEqual(self.editor.clipboard_get(), "select me")

    def test_gui_ctrl_v(self):
        # In this test, we use paste_at_cursor via Ctrl+V
        self.editor.zep.set_text("prefix")
        self.editor.zep.handle_key("$", 0) # moves to 'x'
        # To paste AT the very end with Ctrl+V (which uses paste_at_cursor)
        # we need to be at pos 6. $ doesn't go there in Normal mode.
        # Let's go to Insert mode at the end (A)
        self.editor.zep.handle_key("A", 0)
        
        self.editor.clipboard_clear()
        self.editor.clipboard_append(" extension")
        
        # Ctrl+V
        event = MagicMock()
        event.keysym = "v"
        event.state = 0x4 # Ctrl
        self.editor._on_key_press(event)
        
        self.assertEqual(self.editor.zep.get_text(), "prefix extension")

    def test_gui_ctrl_x(self):
        self.editor.zep.set_text("cut me")
        # Select all
        self.editor.zep.select_all()
        
        # Ctrl+X
        event = MagicMock()
        event.keysym = "x"
        event.state = 0x4 # Ctrl
        self.editor._on_key_press(event)
        
        self.assertEqual(self.editor.zep.get_text(), "")
        self.assertEqual(self.editor.clipboard_get(), "cut me")

    def test_undo_redo_shortcuts(self):
        self.editor.zep.set_text("initial")
        # Move to end and append
        self.editor.zep.handle_key("A", 0)
        self.editor.zep.handle_key(" ", 0)
        self.editor.zep.handle_key("m", 0)
        self.editor.zep.handle_key("o", 0)
        self.editor.zep.handle_key("r", 0)
        self.editor.zep.handle_key("e", 0)
        self.editor.zep.handle_key("Escape", 0)
        
        # Current text: "initial more"
        self.assertEqual(self.editor.zep.get_text(), "initial more")
        
        # Ctrl+Z
        event = MagicMock()
        event.keysym = "z"
        event.state = 0x4 # Ctrl
        self.editor._on_key_press(event)
        self.assertEqual(self.editor.zep.get_text(), "initial")
        
        # Ctrl+Y
        event.keysym = "y"
        self.editor._on_key_press(event)
        self.assertEqual(self.editor.zep.get_text(), "initial more")

if __name__ == "__main__":
    unittest.main()
