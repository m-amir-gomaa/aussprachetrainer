import os
import sys

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from aussprachetrainer.backend import PronunciationBackend
from aussprachetrainer.autocomplete import WordSuggester

def test_core():
    print("=== Aussprachetrainer Core Diagnostic ===")
    
    backend = PronunciationBackend()
    suggester = WordSuggester()
    
    # 1. Test IPA
    print("\n[1] Testing IPA Generation...")
    ipa = backend.get_ipa("Hallo Welt")
    print(f"Result: {ipa}")
    if ipa == "[Error]" or not ipa:
        print("FAIL: IPA generation failed (check espeak-ng)")
    else:
        print("SUCCESS: IPA generated")

    # 2. Test Offline TTS
    print("\n[2] Testing Offline TTS (espeak-ng)...")
    try:
        path = backend.generate_audio("Hallo", online=False)
        print(f"Result path: {path}")
        if path and os.path.exists(path):
            print(f"SUCCESS: Offline audio file exists at {path}")
        else:
            print("FAIL: Offline audio file NOT found")
    except Exception as e:
        print(f"FAIL: Offline TTS raised exception: {e}")

    # 3. Test Online TTS (Optional/Internet dependent)
    print("\n[3] Testing Online TTS (gTTS)...")
    try:
        path = backend.generate_audio("Hallo", online=True)
        print(f"Result path: {path}")
        if path and os.path.exists(path):
            print(f"SUCCESS: Online audio file exists at {path}")
        else:
            print("FAIL: Online audio file NOT found")
    except Exception as e:
        print(f"FAIL: Online TTS raised exception: {e}")

    # 4. Test Autocomplete
    print("\n[4] Testing Autocomplete...")
    suggestions = suggester.get_suggestions("Hal")
    print(f"Suggestions for 'Hal': {suggestions}")
    if suggestions:
        print("SUCCESS: Suggestions returned")
    else:
        print("FAIL: No suggestions returned")

    # 5. Test Database
    print("\n[5] Testing Database...")
    try:
        backend.db.add_entry("Test", "test_ipa", "/tmp/dummy.wav", "Offline", "default")
        history = backend.db.get_history("Test")
        if any(h['text'] == "Test" for h in history):
            print("SUCCESS: Entry found in history")
        else:
            print("FAIL: Entry NOT found in history")
    except Exception as e:
        print(f"FAIL: Database operation failed: {e}")

    # 6. Test Recording & Assessment
    print("\n[6] Testing Recording & Assessment...")
    try:
        print("Recording for 2 seconds... (Say 'Hallo')")
        backend.start_recording()
        import time
        time.sleep(2)
        wav_path = backend.stop_recording()
        print(f"Recorded to: {wav_path}")
        if wav_path and os.path.exists(wav_path):
            print("SUCCESS: Recorded file exists")
            result = backend.assess_pronunciation("Hallo", wav_path, online=False)
            print(f"Assessment Result: {result}")
        else:
            print("FAIL: No recording file produced")
    except Exception as e:
        print(f"FAIL: Recording/Assessment failed: {e}")

    # 7. Test Dialects
    print("\n[7] Testing Dialects...")
    for dialect_name, code in [("Germany", "de-DE"), ("Austria", "de-AT"), ("Switzerland", "de-CH")]:
        backend.set_dialect(code)
        ipa = backend.get_ipa("Guten Tag")
        print(f"Dialect {dialect_name} ({code}) IPA: {ipa}")

    print("\n=== Diagnostic Complete ===")

if __name__ == "__main__":
    test_core()
