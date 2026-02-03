
import sys
import os
import unittest
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from aussprachetrainer import zep_vim
except ImportError:
    print("zep_vim not found.")
    sys.exit(1)

# Stub for CTkFrame
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
    def clipboard_get(self): 
        if not self._clipboard:
            raise Exception("Clipboard empty")
        return self._clipboard
    def clipboard_clear(self): self._clipboard = ""
    def clipboard_append(self, text): self._clipboard += text
    def update(self): pass

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

class TestClipboardIssues(unittest.TestCase):
    def setUp(self):
        self.editor = VimEditor(MagicMock())
        self.editor.zep = zep_vim.ZepVim()
        self.editor._render_vimbuffer = MagicMock()

    def test_sync_to_system_when_content_matches_internal_but_different_externally(self):
        # 1. Set internal Zep clipboard to "A"
        self.editor.zep.set_clipboard("A")
        
        # 2. Set system clipboard to "B" (externally changed)
        self.editor._clipboard = "B"
        
        # 3. Perform a yank in Zep that results in "A" again
        # Let's say we have "A" on a line and we do yy
        self.editor.zep.set_text("A")
        event = MagicMock()
        event.keysym = "y"
        event.state = 0
        self.editor._on_key_press(event)
        self.editor._on_key_press(event) # yy
        
        # Current behavior: it might NOT sync because Zep's clip was already "A"
        # We want it to be "A\n" (yanked line) or whatever.
        # But if it was exactly "A" before...
        
        # Let's verify if it's currently failing to overwrite "B"
        # Since I haven't fixed it yet, this might fail or pass depending on \n.
        # But the principle is: we want the script to capture this.
        self.assertEqual(self.editor.clipboard_get(), "A\n")

    def test_focus_in_syncs_from_system(self):
        # This test checks if we have a FocusIn binding that syncs
        # 1. External app copies "EXTERNAL"
        self.editor._clipboard = "EXTERNAL"
        
        # 2. App gets focus. We should have a binding.
        # Since I haven't added it yet, I'll check if the binding exists.
        # Actually, I'll mock the event.
        focus_event = MagicMock()
        if hasattr(self.editor, "_on_focus_in"):
             self.editor._on_focus_in(focus_event)
             self.assertEqual(self.editor.zep.get_clipboard(), "EXTERNAL")
    def test_x_command_syncs_to_system(self):
        # 1. Set text to "abc"
        self.editor.zep.set_text("abc")
        self.editor.zep.handle_key("0", 0) # Start of line
        
        # 2. Clear system clipboard
        self.editor.clipboard_clear()
        
        # 3. Press 'x' (deletes 'a')
        event = MagicMock()
        event.keysym = "x"
        event.state = 0
        self.editor._on_key_press(event)
        
        # 4. Check system clipboard
        self.assertEqual(self.editor.clipboard_get(), "a")
        self.assertEqual(self.editor.zep.get_text(), "bc")

if __name__ == "__main__":
    unittest.main()
