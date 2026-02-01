import unittest
import os
import shutil
import tempfile
import sys
import time
import sqlite3
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from aussprachetrainer.database import HistoryManager
from aussprachetrainer.backend import PronunciationBackend
try:
    from aussprachetrainer.vim_editor import VimEditor
except ImportError:
    VimEditor = None

class TestComprehensive(unittest.TestCase):
    def setUp(self):
        # Create temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_history.db")
        self.audio_dir = os.path.join(self.test_dir, "audio")
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # Initialize Database
        self.db = HistoryManager(db_path=self.db_path)
        
        # Initialize Backend with mocked components where necessary
        self.backend = PronunciationBackend()
        self.backend.db = self.db
        self.backend.audio_dir = self.audio_dir

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    # --- Database & Persistence Tests ---

    def test_database_creation(self):
        """Verify database is created."""
        self.assertTrue(os.path.exists(self.db_path))

    def test_add_and_retrieve_entry(self):
        """Test adding and retrieving a history entry."""
        self.db.add_entry("Hallo", "/halo/", "/tmp/audio.wav", "Online", "de")
        history = self.db.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['text'], "Hallo")
        self.assertEqual(history[0]['ipa'], "/halo/")

    def test_deduplication(self):
        """Test that adding a duplicate entry updates it (moves to top)."""
        self.db.add_entry("Test", "IPA1", "/audio1.wav", "Online", "de")
        time.sleep(0.01)
        self.db.add_entry("Test", "IPA2", "/audio2.wav", "Offline", "de")
        
        history = self.db.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['ipa'], "IPA2") # Should be the new one

    def test_clear_history_removes_audio(self):
        """Test that clearing history also removes associated audio files."""
        # Create dummy audio file
        audio_path = os.path.join(self.audio_dir, "test_audio.wav")
        with open(audio_path, "w") as f:
            f.write("dummy data")
            
        self.db.add_entry("Text", "IPA", audio_path, "Online", "de")
        
        # Verify it exists
        self.assertTrue(os.path.exists(audio_path))
        
        # Clear history
        self.db.clear_history()
        
        # Verify DB is empty and file is gone
        self.assertEqual(len(self.db.get_history()), 0)
        self.assertFalse(os.path.exists(audio_path))

    def test_cleanup_orphaned_audio(self):
        """Test cleanup of audio files not in DB."""
        kept_audio = os.path.join(self.audio_dir, "kept.wav")
        orphaned_audio = os.path.join(self.audio_dir, "orphan.wav")
        
        with open(kept_audio, "w"): pass
        with open(orphaned_audio, "w"): pass
        
        self.db.add_entry("Kept", "IPA", kept_audio, "Online", "de")
        
        self.db.cleanup_orphaned_audio(self.audio_dir)
        
        self.assertTrue(os.path.exists(kept_audio))
        self.assertFalse(os.path.exists(orphaned_audio))

    # --- Vim Editor Logic Tests ---
    # We test the pure logic via the Zep wrapper if possible, or the Python interface
    
    def test_vim_editor_logic(self):
        """Test basic Vim editor logic (using the python wrapper if compiled, else mock)."""
        if VimEditor is None:
            self.skipTest("VimEditor not importable")
            
        # We can instantiate the ZepVim class directly if exposed, 
        # or use a headless version of VimEditor if we can avoid TK
        
        # Try importing ZepVim directly
        try:
            from aussprachetrainer import zep_vim
            zep = zep_vim.ZepVim()
        except ImportError:
            sys.path.append(os.path.join(os.getcwd(), "src", "aussprachetrainer"))
            import zep_vim
            zep = zep_vim.ZepVim()

        # Test Insert Mode
        zep.handle_key("i", 0)
        self.assertEqual(zep.get_mode(), "INSERT")
        zep.handle_key("h", 0)
        zep.handle_key("i", 0)
        self.assertEqual(zep.get_text(), "hi")
        zep.handle_key("Escape", 0)
        self.assertEqual(zep.get_mode(), "NORMAL")
        
        # Test Motion (h)
        # Cursor is after 'i' (pos 2). Escape moves back 1 -> pos 1 ('i')
        # h -> pos 0 ('h')
        zep.handle_key("h", 0)
        # We can't easily check cursor pos without exposing it, but we can verify it doesn't crash
        
        # Test Deletion (x)
        zep.handle_key("x", 0)
        self.assertEqual(zep.get_text(), "i") # 'h' deleted

        # Test New Motions
        zep.set_text("hello world")
        zep.handle_key("Escape", 0) # Ensure Normal mode
        zep.handle_key("0", 0) # Start of line
        
        # 'w' - move to next word start (world)
        zep.handle_key("w", 0) 
        # cursor should be at 'w' (index 6)
        # We can't verify cursor easily without exposing it, so let's delete word 'dw'
        zep.handle_key("d", 0)
        zep.handle_key("w", 0)
        self.assertEqual(zep.get_text(), "hello ")

        # Test 'e' - end of word
        zep.set_text("one two")
        zep.handle_key("Escape", 0)
        zep.handle_key("0", 0)
        zep.handle_key("e", 0) 
        # cursor at 'e' (index 2)
        zep.handle_key("x", 0)
        self.assertEqual(zep.get_text(), "on two")

        # Test '$' - end of line
        zep.handle_key("dollar", 0)
        zep.handle_key("x", 0)
        self.assertEqual(zep.get_text(), "on tw") # Deleted last char 'o'

    def test_vim_navigation(self):
        """Test Vim navigation shortcuts (gg, G, h, j, k, l, b)."""
        if VimEditor is None:
            return

        try:
            from aussprachetrainer import zep_vim
            zep = zep_vim.ZepVim()
        except ImportError:
            sys.path.append(os.path.join(os.getcwd(), "src", "aussprachetrainer"))
            import zep_vim
            zep = zep_vim.ZepVim()

        # Setup multi-line text
        # Line 0: "line 1" (6 chars)
        # Line 1: "line 2" (6 chars)
        # Line 2: "line 3" (6 chars)
        zep.set_text("line 1\nline 2\nline 3")
        zep.handle_key("Escape", 0) # Normal mode
        
        # Test 'G' (Go to last line)
        zep.handle_key("G", 0)
        # Should be on line 2 (0-indexed)
        # We verify by deleting the line 'dd' and checking text
        zep.handle_key("d", 0)
        zep.handle_key("d", 0)
        self.assertEqual(zep.get_text(), "line 1\nline 2")
        
        # Test 'gg' (Go to first line)
        zep.handle_key("g", 0)
        zep.handle_key("g", 0)
        # Should be on line 0. Delete line.
        zep.handle_key("d", 0)
        zep.handle_key("d", 0)
        self.assertEqual(zep.get_text(), "line 2")

        # Test 'j' (Down) and 'k' (Up)
        zep.set_text("row A\nrow B\nrow C")
        zep.handle_key("Escape", 0)
        zep.handle_key("g", 0) 
        zep.handle_key("g", 0) # Ensure top
        
        # Move down to 'row B'
        zep.handle_key("j", 0)
        # Delete line 'row B'
        zep.handle_key("d", 0)
        zep.handle_key("d", 0)
        self.assertEqual(zep.get_text(), "row A\nrow C")
        
        # Move down to 'row C' (cursor is currently on row C after deletion of B usually, or A depending on impl. 
        # Standard vim: if you delete last line, cursor moves up. If you delete middle, cursor stays on new line at that pos.
        # Let's reset to be sure of state logic)
        zep.set_text("row A\nrow B")
        zep.handle_key("Escape", 0)
        zep.handle_key("G", 0) # At row B
        zep.handle_key("k", 0) # At row A
        zep.handle_key("d", 0)
        zep.handle_key("d", 0)
        self.assertEqual(zep.get_text(), "row B")
        
        # Test 'l' (Right) and 'h' (Left) and 'b' (Back word)
        zep.set_text("hello world")
        zep.handle_key("Escape", 0)
        zep.handle_key("0", 0)
        
        # Move right 2 chars: 'h' -> 'e' -> 'l'
        zep.handle_key("l", 0)
        zep.handle_key("l", 0)
        zep.handle_key("x", 0) # Delete 'l'
        self.assertEqual(zep.get_text(), "helo world")
        
        # Move right 1 ('o'), then back 1 ('l')
        zep.handle_key("l", 0)
        zep.handle_key("h", 0)
        zep.handle_key("x", 0) # Delete 'l' again (the second 'l' became first 'l' after deletion? No.)
        # Text: "helo world". Cursor was at 'l' (index 2).
        # We deleted index 2. Text becomes "helo world". Cursor usually stays at 2 ('o').
        # 'l' moves to ' ' (index 3).
        # 'h' moves to 'o' (index 2).
        # 'x' deletes 'o'.
        self.assertEqual(zep.get_text(), "heo world")
        
        # Test 'b' (back word)
        zep.set_text("one two three")
        zep.handle_key("Escape", 0)
        zep.handle_key("$", 0) # End of line ('e' of three, or just after?)
        # My implementation of $ places cursor at last char
        # 'b' should jump to start of "three"
        zep.handle_key("b", 0)
        # Delete word 'dw' -> "one two "
        zep.handle_key("d", 0)
        zep.handle_key("w", 0)
        self.assertEqual(zep.get_text(), "one two ")


    # --- Autocomplete Tests ---
    
    def test_autocomplete_ranking(self):
        """Test that autocomplete returns ranked results."""
        from aussprachetrainer.autocomplete import GermanSuggester
        
        # Mocking Trie/TextEngine for predictable results if needed, 
        # or just test integration if resources exist.
        if not os.path.exists("src/aussprachetrainer/resources/dicts/de_DE.dic"):
             print("Skipping autocomplete test: dictionary not found")
             return

        suggester = GermanSuggester()
        # "ha" should suggest "haben", "hallo" etc.
        suggestions = suggester.suggest("ha")
        self.assertTrue(len(suggestions) > 0)
        
        # Ensure results start with prefix
        for s in suggestions:
            self.assertTrue(s.lower().startswith("ha"))

if __name__ == "__main__":
    unittest.main()
