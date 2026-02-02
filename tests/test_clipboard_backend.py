
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from aussprachetrainer import zep_vim
except ImportError:
    print("zep_vim not found.")
    sys.exit(1)

class TestClipboardSync(unittest.TestCase):
    def test_get_set_clipboard(self):
        zep = zep_vim.ZepVim()
        zep.set_clipboard("test content")
        self.assertEqual(zep.get_clipboard(), "test content")

    def test_yank_updates_clipboard(self):
        zep = zep_vim.ZepVim()
        zep.set_text("hello")
        # Yank 5 characters (hello)
        # In Normal mode: y5l
        # But wait, our simplified wrapper handles 'y' as an operator waiting for motion.
        # Or 'yy' for line.
        zep.handle_key("y", 0)
        zep.handle_key("y", 0)
        self.assertEqual(zep.get_clipboard(), "hello\n")

if __name__ == "__main__":
    unittest.main()
