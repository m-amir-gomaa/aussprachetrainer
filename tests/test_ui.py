import unittest
import tkinter as tk
import time
import os
import sys
import threading

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))
from aussprachetrainer.gui import App

class TestUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We need a display. On headless systems this might fail.
        cls.app = App()
        cls.app.withdraw() # Hide window during test
        # Give it a moment to initialize
        cls.app.update()

    @classmethod
    def tearDownClass(cls):
        cls.app.destroy()

    def test_history_toggle(self):
        self.app.toggle_history_panel()
        self.assertTrue(self.app.history_focused)
        # focus_get() might return None if window is withdrawn/minimized
        if self.app.state() != "withdrawn":
            self.assertEqual(str(self.app.focus_get()), str(self.app.search_entry._entry))
        
        self.app.toggle_history_panel()
        self.assertFalse(self.app.history_focused)

    def test_recording_toggle(self):
        # Simulate Ctrl+r
        initial_state = self.app.backend.recording
        self.app.toggle_recording()
        self.assertNotEqual(initial_state, self.app.backend.recording)
        # Stop it
        self.app.toggle_recording()
        self.assertFalse(self.app.backend.recording)

    def test_vim_propagation(self):
        # Focus VimEditor
        self.app.input_text.focus_set()
        self.app.update()
        
        # Manually trigger a key event that should NOT be blocked
        # e.g. Ctrl+h
        # Instead of event_generate which might be flakey in CI, 
        # we check the logic in VimEditor._on_key_press returning None
        
        class FakeEvent:
            def __init__(self, keysym, state):
                self.keysym = keysym
                self.state = state # 4 for Control
        
        # Test propagation for Ctrl+h
        res = self.app.input_text._on_key_press(FakeEvent("h", 4))
        self.assertEqual(res, None, "Ctrl+h should propagate (return None)")
        
        # Test propagation for Ctrl+r
        res = self.app.input_text._on_key_press(FakeEvent("r", 4))
        self.assertEqual(res, None, "Ctrl+r should propagate")

    def test_vim_blocking(self):
        # Normal keys should return "break"
        class FakeEvent:
            def __init__(self, keysym, state):
                self.keysym = keysym
                self.state = state
        
        res = self.app.input_text._on_key_press(FakeEvent("x", 0))
        self.assertEqual(res, "break", "Normal Vim keys should block propagation")

    def test_vim_rendering(self):
        """Test that _render_vimbuffer runs without errors for various characters."""
        ve = self.app.input_text
        # Test normal text
        ve.set_text("Hello World")
        ve._render_vimbuffer()
        self.assertTrue(len(ve.canvas.find_all()) > 0)
        
        # Test Tabs
        ve.set_text("Tabs\tHere")
        ve._render_vimbuffer()
        
        # Test Empty
        ve.set_text("")
        ve._render_vimbuffer()
        
        # Test Newlines
        ve.set_text("Line 1\nLine 2")
        ve._render_vimbuffer()

    def test_cursor_blinking(self):
        """Test that cursor stops blinking in Normal mode."""
        ve = self.app.input_text
        # Default is Normal mode
        self.assertEqual(ve.zep.get_mode(), "NORMAL")
        
        # Simulate blink timer tick
        initial_visibility = ve.cursor_visible
        ve._blink_cursor()
        # In Normal mode, visibility should ALWAYS be True, regardless of toggle
        self.assertTrue(ve.cursor_visible)
        
        # Switch to Insert
        ve.zep.handle_key("i", 0)
        self.assertEqual(ve.zep.get_mode(), "INSERT")
        
        # Blink should toggle
        ve.cursor_visible = True
        ve._blink_cursor()
        self.assertFalse(ve.cursor_visible)
        ve._blink_cursor()
        self.assertTrue(ve.cursor_visible)

if __name__ == "__main__":
    unittest.main()
