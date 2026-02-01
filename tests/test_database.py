import unittest
import os
import tempfile
import shutil
import sys
import time

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))
from aussprachetrainer.database import HistoryManager

class TestHistoryManager(unittest.TestCase):
    def setUp(self):
        # Create temporary database for testing
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_history.db")
        self.audio_dir = os.path.join(self.test_dir, "audio")
        os.makedirs(self.audio_dir, exist_ok=True)
        
        self.db = HistoryManager(db_path=self.db_path)
    
    def tearDown(self):
        # Clean up temporary files
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_init_creates_db(self):
        """Verify database file is created on initialization."""
        self.assertTrue(os.path.exists(self.db_path))
    
    def test_add_entry(self):
        """Add entry and verify it's stored correctly."""
        self.db.add_entry("Hallo Welt", "/haloː vɛlt/", "/path/to/audio.wav", "Offline", "de+m3")
        
        history = self.db.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["text"], "Hallo Welt")
        self.assertEqual(history[0]["ipa"], "/haloː vɛlt/")
        self.assertEqual(history[0]["audio_path"], "/path/to/audio.wav")
        self.assertEqual(history[0]["mode"], "Offline")
        self.assertEqual(history[0]["voice_id"], "de+m3")
    
    def test_add_duplicate_removes_old(self):
        """Verify adding duplicate text removes old entry (deduplication)."""
        self.db.add_entry("Test", "IPA1", "/audio1.wav", "Online", "de")
        self.db.add_entry("Other", "IPA2", "/audio2.wav", "Offline", "de+m3")
        self.db.add_entry("Test", "IPA3", "/audio3.wav", "Auto", "de")
        
        history = self.db.get_history()
        self.assertEqual(len(history), 2)
        
        # The "Test" entry should be the newer one
        test_entries = [h for h in history if h["text"] == "Test"]
        self.assertEqual(len(test_entries), 1)
        self.assertEqual(test_entries[0]["ipa"], "IPA3")
        self.assertEqual(test_entries[0]["audio_path"], "/audio3.wav")
    
    def test_get_history(self):
        """Retrieve all entries in reverse chronological order."""
        self.db.add_entry("First", "IPA1", "/audio1.wav", "Online", "de")
        time.sleep(0.01)
        self.db.add_entry("Second", "IPA2", "/audio2.wav", "Offline", "de+m3")
        time.sleep(0.01)
        self.db.add_entry("Third", "IPA3", "/audio3.wav", "Auto", "de")
        
        history = self.db.get_history()
        self.assertEqual(len(history), 3)
        # Most recent first
        self.assertEqual(history[0]["text"], "Third")
        self.assertEqual(history[1]["text"], "Second")
        self.assertEqual(history[2]["text"], "First")
    
    def test_get_history_with_search(self):
        """Search functionality filters entries correctly."""
        self.db.add_entry("Guten Morgen", "IPA1", "/audio1.wav", "Online", "de")
        self.db.add_entry("Guten Tag", "IPA2", "/audio2.wav", "Offline", "de+m3")
        self.db.add_entry("Hallo", "IPA3", "/audio3.wav", "Auto", "de")
        
        # Search for "Guten"
        results = self.db.get_history(search_query="Guten")
        self.assertEqual(len(results), 2)
        self.assertTrue(all("Guten" in r["text"] for r in results))
        
        # Search for "Hallo"
        results = self.db.get_history(search_query="Hallo")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "Hallo")
    
    def test_delete_entry(self):
        """Delete entry by ID."""
        self.db.add_entry("To Delete", "IPA", "/audio.wav", "Online", "de")
        history = self.db.get_history()
        entry_id = history[0]["id"]
        
        self.db.delete_entry(entry_id)
        
        history_after = self.db.get_history()
        self.assertEqual(len(history_after), 0)
    
    def test_clear_history(self):
        """Clear all entries from database."""
        self.db.add_entry("Entry 1", "IPA1", "/audio1.wav", "Online", "de")
        self.db.add_entry("Entry 2", "IPA2", "/audio2.wav", "Offline", "de+m3")
        self.db.add_entry("Entry 3", "IPA3", "/audio3.wav", "Auto", "de")
        
        self.db.clear_history()
        
        history = self.db.get_history()
        self.assertEqual(len(history), 0)
    
    def test_audio_persistence(self):
        """Verify audio files are tracked correctly in database."""
        # Create dummy audio files
        audio1 = os.path.join(self.audio_dir, "audio1.wav")
        audio2 = os.path.join(self.audio_dir, "audio2.wav")
        
        with open(audio1, "w") as f:
            f.write("dummy audio 1")
        with open(audio2, "w") as f:
            f.write("dummy audio 2")
        
        # Add entries with these audio paths
        self.db.add_entry("Test 1", "IPA1", audio1, "Online", "de")
        self.db.add_entry("Test 2", "IPA2", audio2, "Offline", "de+m3")
        
        history = self.db.get_history()
        self.assertEqual(len(history), 2)
        
        # Verify audio paths are stored
        audio_paths = {h["audio_path"] for h in history}
        self.assertIn(audio1, audio_paths)
        self.assertIn(audio2, audio_paths)
    
    def test_cleanup_orphaned_audio(self):
        """Verify cleanup removes audio files not in database."""
        # Create audio files
        audio1 = os.path.join(self.audio_dir, "audio1.wav")
        audio2 = os.path.join(self.audio_dir, "audio2.wav")
        orphan = os.path.join(self.audio_dir, "orphan.wav")
        
        with open(audio1, "w") as f:
            f.write("dummy audio 1")
        with open(audio2, "w") as f:
            f.write("dummy audio 2")
        with open(orphan, "w") as f:
            f.write("orphaned audio")
        
        # Add only audio1 and audio2 to database
        self.db.add_entry("Test 1", "IPA1", audio1, "Online", "de")
        self.db.add_entry("Test 2", "IPA2", audio2, "Offline", "de+m3")
        
        # Verify all files exist before cleanup
        self.assertTrue(os.path.exists(audio1))
        self.assertTrue(os.path.exists(audio2))
        self.assertTrue(os.path.exists(orphan))
        
        # Run cleanup
        self.db.cleanup_orphaned_audio(self.audio_dir)
        
        # Verify orphan is removed but referenced files remain
        self.assertTrue(os.path.exists(audio1))
        self.assertTrue(os.path.exists(audio2))
        self.assertFalse(os.path.exists(orphan))

if __name__ == "__main__":
    unittest.main()
