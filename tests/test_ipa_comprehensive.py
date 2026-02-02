
import sys
import os
import unittest

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from aussprachetrainer.backend import PronunciationBackend

class TestIPAComprehensive(unittest.TestCase):
    def setUp(self):
        self.backend = PronunciationBackend()

    def test_image_allophones(self):
        test_cases = [
            # Consonants
            ("Post", "pʰ"),    # Aspirated p
            ("Stab", "b̥"),     # Lenis voiceless b
            ("Tag", "tʰ"),     # Aspirated t
            ("Bad", "d̥"),      # Lenis voiceless d
            ("Kind", "kʰ"),    # Aspirated k
            ("Weg", "g̊"),      # Lenis voiceless g
            ("Vase", "v"),     # Voiced v
            ("aktiv", "v̥"),    # Lenis voiceless v
            ("Sonne", "z"),    # Voiced z (s- onset)
            ("Haus", "s"),     # Voiceless s
            ("reisen", "z"),   # Medial z (voiced)
            ("Haus", "s"),     # Voiceless s (final)
            ("Hose", "z"),     # Medial z (voiced)
            ("Bus", "s"),      # Voiceless s (final, originally s)
            ("Gras", "z̥"),     # Lenis voiceless z (final s originally voiced)
            ("Ingenieur", "ʒ"),# Voiced ʒ
            ("Garage", "ʒ̊"),   # Lenis voiceless ʒ (final)
            
            # Vowels & Glides
            ("Familie", "i̯"),  # Glide i
            ("Auto", "u̯"),     # Glide u
            ("Bauer", "u̯"),    # Glide u
            ("hier", "iːɐ̯"),   # Vocalic R glide
            ("Vater", "ɐ"),    # Vocalic R final
            ("rot", "ʁ"),      # Uvular R
            ("Bahn", "aː"),    # Long a
            ("Bann", "an"),    # Short a
            ("Sonne", "ɔ"),    # Open o
            ("Boot", "oː"),    # Long o
            
            # Diphthongs
            ("Wein", "ai̯"),    # Diphthong ei/ai
            ("Haus", "au̯"),    # Diphthong au
            ("neu", "ɔʏ̯"),     # Diphthong eu/äu
        ]

        print("\n--- IPA Comprehensive Test Results ---")
        for word, expected_part in test_cases:
            ipa = self.backend.get_ipa(word)
            print(f"Word: {word:12} IPA: {ipa:20} Expected symbol: {expected_part}")
            self.assertIn(expected_part, ipa, f"Word '{word}' IPA '{ipa}' missing expected symbol '{expected_part}'")

if __name__ == "__main__":
    unittest.main()
