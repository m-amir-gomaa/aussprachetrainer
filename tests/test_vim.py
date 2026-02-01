import sys
import os
import unittest

# Add src to path to find zep_vim (if built)
sys.path.append(os.path.join(os.getcwd(), "src"))
sys.path.append(os.path.join(os.getcwd(), "src", "aussprachetrainer"))

try:
    import zep_vim
except ImportError:
    print("Could not import zep_vim. Make sure it's built.")
    sys.exit(1)

class TestVimEngine(unittest.TestCase):
    def setUp(self):
        self.zep = zep_vim.ZepVim()
        self.zep.set_text("Hello World\nVim is great\nPython is powerful")

    def test_motions(self):
        # Initial pos (0,0)
        self.assertEqual(self.zep.get_cursor(), (0, 0))
        
        # Move right (l)
        self.zep.handle_key("l", 0)
        self.assertEqual(self.zep.get_cursor(), (0, 1))
        
        # Move down (j)
        self.zep.handle_key("j", 0)
        self.assertEqual(self.zep.get_cursor(), (1, 1))
        
        # Move to end of line ($)
        self.zep.handle_key("dollar", 0)
        self.assertEqual(self.zep.get_cursor(), (1, 12)) 

    def test_deletion(self):
        # Delete word (dw)
        self.zep.handle_key("d", 0)
        self.zep.handle_key("w", 0)
        self.assertNotIn("Hello", self.zep.get_text())
        
        # Delete line (dd)
        cur_line = self.zep.get_text().split("\n")[0]
        self.zep.handle_key("d", 0)
        self.zep.handle_key("d", 0)
        self.assertNotIn(cur_line, self.zep.get_text())

    def test_undo_redo(self):
        original = self.zep.get_text()
        self.zep.handle_key("x", 0)
        self.assertNotEqual(self.zep.get_text(), original)
        
        self.zep.handle_key("u", 0)
        self.assertEqual(self.zep.get_text(), original)
        
        # Redo (Ctrl+r) -> modifiers=4 for Ctrl
        self.zep.handle_key("r", 4)
        self.assertNotEqual(self.zep.get_text(), original)

    def test_counts(self):
        # 3l (move 3 right)
        self.zep.handle_key("3", 0)
        self.zep.handle_key("l", 0)
        self.assertEqual(self.zep.get_cursor(), (0, 3))
        
        # Reset pos
        self.zep.set_text("Line 1\nLine 2\nLine 3\nLine 4")
        self.zep.handle_key("g", 0)
        self.zep.handle_key("g", 0)
        
        # 2dd (delete 2 lines)
        self.zep.handle_key("2", 0)
        self.zep.handle_key("d", 0)
        self.zep.handle_key("d", 0)
        lines = self.zep.get_text().split("\n")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "Line 3")

    def test_nested_counts(self):
        self.zep.set_text("one two three four five six seven eight")
        # 3d2w -> 3 * 2 = 6 words
        self.zep.handle_key("3", 0)
        self.zep.handle_key("d", 0)
        self.zep.handle_key("2", 0)
        self.zep.handle_key("w", 0)
        self.assertEqual(self.zep.get_text().strip(), "seven eight")

    def test_visual_mode(self):
        self.zep.handle_key("v", 0)
        self.assertEqual(self.zep.get_mode(), "VISUAL")
        self.zep.handle_key("w", 0) # Select first word
        self.zep.handle_key("d", 0) # Delete selection
        self.assertNotIn("Hello", self.zep.get_text())
        self.assertEqual(self.zep.get_mode(), "NORMAL")

    def test_replace_mode(self):
        self.zep.handle_key("R", 0)
        self.assertEqual(self.zep.get_mode(), "REPLACE")
        self.zep.handle_key("A", 0)
        self.zep.handle_key("B", 0)
        self.zep.handle_key("C", 0)
        text = self.zep.get_text()
        self.assertTrue(text.startswith("ABClo"))

    def test_single_replace(self):
        # rZ on "Hello World" -> "Zello World"
        self.zep.handle_key("r", 0)
        self.zep.handle_key("Z", 0)
        self.assertTrue(self.zep.get_text().startswith("Zello"))
        
        # 3rY on "Zello World" -> "YYYlo World"
        self.zep.handle_key("3", 0)
        self.zep.handle_key("r", 0)
        self.zep.handle_key("Y", 0)
        self.assertTrue(self.zep.get_text().startswith("YYYlo"))

    def test_r_edge_cases(self):
        # Should not replace newline
        self.zep.set_text("A\nB")
        self.zep.handle_key("r", 0)
        self.zep.handle_key("X", 0)
        self.assertEqual(self.zep.get_text(), "X\nB")
        
        self.zep.handle_key("l", 0) # On \n
        self.zep.handle_key("r", 0)
        self.zep.handle_key("Y", 0)
        self.assertEqual(self.zep.get_text(), "X\nB", "r should not replace newline")

    def test_jj_bug(self):
        # Insert a newline first to test start of line behavior
        self.zep.set_text("\nSomething")
        self.zep.handle_key("j", 0)
        self.zep.handle_key("k", 0)
        self.zep.handle_key("i", 0)
        self.zep.handle_key("j", 0)
        self.zep.handle_key("j", 0)
        self.assertEqual(self.zep.get_mode(), "NORMAL")
        # Check that no extra 'j' remained
        text = self.zep.get_text()
        self.assertTrue(text.startswith("\nSomething"))

    def test_o_first_line(self):
        self.zep.set_text("First")
        self.zep.handle_key("o", 0)
        self.assertEqual(self.zep.get_text(), "First\n")
        self.assertEqual(self.zep.get_cursor(), (1, 0))

    def test_visual_line(self):
        self.zep.set_text("Line 1\nLine 2\nLine 3")
        self.zep.handle_key("V", 0) # Normal mode, V -> Visual Line
        self.zep.handle_key("j", 0) # Select Line 1 and 2
        self.zep.handle_key("d", 0) # Delete
        self.assertEqual(self.zep.get_text(), "Line 3")

    def test_replace_word(self):
        self.zep.set_text("Hello World")
        # Cursor at (0,0) by default
        self.zep.replace_current_word("Antigravity")
        self.assertEqual(self.zep.get_text(), "Antigravity World")

if __name__ == "__main__":
    unittest.main()
