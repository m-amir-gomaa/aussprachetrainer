
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

import tkinter as tk
import customtkinter as ctk

class TestSearchUndoRedo(unittest.TestCase):
    @patch('customtkinter.CTkImage')
    @patch('customtkinter.CTkLabel')
    @patch('aussprachetrainer.gui.PronunciationBackend')
    @patch('aussprachetrainer.gui.GermanSuggester')
    @patch('aussprachetrainer.gui.ConfigManager')
    def setUp(self, mock_config_cls, mock_suggester, mock_backend, mock_label, mock_image):
        self.root = ctk.CTk()
        
        # Setup mock config
        self.mock_config = mock_config_cls.return_value
        self.mock_config.get.side_effect = lambda k: {
            "font_size": 16, "font_family": "Roboto Mono",
            "is_fullscreen": False, "window_state": "normal",
            "window_width": 1200, "window_height": 800,
            "window_x": 0, "window_y": 0,
            "connection_mode": "Online", "dialect": "Germany (Standard)",
            "sidebar_width": 300, "history_panel_width": 300
        }.get(k)
        
        from aussprachetrainer.gui import App
        self.app = App()
        self.app.flag_image = None
        
    def tearDown(self):
        self.app.destroy()
        self.root.destroy()

    def test_search_undo_logic(self):
        entry = self.app.search_entry
        
        # Simulate typing "hello"
        entry.delete(0, "end")
        entry.insert(0, "h")
        self.app._search_push_state()
        entry.insert("end", "e")
        self.app._search_push_state()
        entry.insert("end", "llo")
        self.app._search_push_state()
        
        self.assertEqual(entry.get(), "hello")
        
        # Undo "llo"
        self.app._search_undo()
        self.assertEqual(entry.get(), "he")
        
        # Undo "e"
        self.app._search_undo()
        self.assertEqual(entry.get(), "h")
        
        # Redo "e"
        self.app._search_redo()
        self.assertEqual(entry.get(), "he")
        
        # Redo "llo"
        self.app._search_redo()
        self.assertEqual(entry.get(), "hello")

if __name__ == "__main__":
    unittest.main()
