import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from aussprachetrainer.text_engine_wrapper import TextEngine, ACTION_BOLD, ACTION_UNDO

def test_text_engine():
    print("Initializing TextEngine...")
    engine = TextEngine()
    if not engine.is_available():
        print("ERROR: TextEngine shared library not found. Make sure it's compiled.")
        return

    print("Testing German character mappings (Alt + key):")
    # Alt + A -> ä (char code 228)
    char = engine.get_german_char(ord('a'), alt=True, shift=False)
    print(f"Alt + a -> {char} (Expected: ä)")
    
    char = engine.get_german_char(ord('A'), alt=True, shift=True)
    print(f"Alt + Shift + A -> {char} (Expected: Ä)")

    char = engine.get_german_char(ord('s'), alt=True, shift=False)
    print(f"Alt + s -> {char} (Expected: ß)")

    print("\nTesting Shortcut actions (Ctrl + key):")
    # Ctrl + B -> ACTION_BOLD (1)
    action = engine.get_action(ord('b'), ctrl=True, shift=False)
    print(f"Ctrl + b -> Action {action} (Expected: {ACTION_BOLD})")
    
    # Ctrl + Z -> ACTION_UNDO (4)
    action = engine.get_action(ord('z'), ctrl=True, shift=False)
    print(f"Ctrl + z -> Action {action} (Expected: {ACTION_UNDO})")

    print("\nVerification Complete!")

if __name__ == "__main__":
    test_text_engine()
