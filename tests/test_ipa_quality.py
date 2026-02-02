
import sys
import os
import unittest

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from aussprachetrainer.backend import PronunciationBackend, GermanIPAProcessor

class TestIPAQuality(unittest.TestCase):
    def setUp(self):
        self.backend = PronunciationBackend()

    def test_aspiration(self):
        # Post should have aspirated p [pʰ]
        ipa = self.backend.get_ipa("Post")
        print(f"DEBUG: 'Post' IPA: {ipa}")
        self.assertIn("pʰ", ipa)
        
        # Tag should have aspirated t [tʰ]
        ipa = self.backend.get_ipa("Tag")
        print(f"DEBUG: 'Tag' IPA: {ipa}")
        self.assertIn("tʰ", ipa)
        
        # Kind should have aspirated k [kʰ]
        ipa = self.backend.get_ipa("Kind")
        print(f"DEBUG: 'Kind' IPA: {ipa}")
        self.assertIn("kʰ", ipa)

    def test_no_aspiration_after_s(self):
        # Stein should NOT have aspirated t
        ipa = self.backend.get_ipa("Stein")
        print(f"DEBUG: 'Stein' IPA: {ipa}")
        self.assertNotIn("tʰ", ipa)
        
        # Spiel should NOT have aspirated p
        ipa = self.backend.get_ipa("Spiel")
        print(f"DEBUG: 'Spiel' IPA: {ipa}")
        self.assertNotIn("pʰ", ipa)

    def test_glottal_stop(self):
        # Apfel should have glottal stop [ʔ] before A
        ipa = self.backend.get_ipa("Apfel")
        print(f"DEBUG: 'Apfel' IPA: {ipa}")
        self.assertIn("ʔ", ipa)
        
        # Auto should have glottal stop [ʔ] before A
        ipa = self.backend.get_ipa("Auto")
        print(f"DEBUG: 'Auto' IPA: {ipa}")
        self.assertIn("ʔ", ipa)
        
        # Ende should have glottal stop
        ipa = self.backend.get_ipa("Ende")
        print(f"DEBUG: 'Ende' IPA: {ipa}")
        self.assertIn("ʔ", ipa)

    def test_vocalized_r(self):
        # Vater should end in vocalized R [ɐ]
        ipa = self.backend.get_ipa("Vater")
        print(f"DEBUG: 'Vater' IPA: {ipa}")
        self.assertTrue(ipa.endswith("ɐ"))
        
        # hier should have vocalic R coda [ɐ̯]
        ipa = self.backend.get_ipa("hier")
        print(f"DEBUG: 'hier' IPA: {ipa}")
        self.assertIn("ɐ̯", ipa)

    def test_uvular_r(self):
        # rot should start with uvular R [ʁ]
        ipa = self.backend.get_ipa("rot")
        print(f"DEBUG: 'rot' IPA: {ipa}")
        self.assertIn("ʁ", ipa)

    def test_diphthongs(self):
        # Haus should use non-syllabic diacritic [aʊ̯]
        ipa = self.backend.get_ipa("Haus")
        print(f"DEBUG: 'Haus' IPA: {ipa}")
        self.assertIn("aʊ̯", ipa)
        
        # Wein should use [aɪ̯]
        ipa = self.backend.get_ipa("Wein")
        print(f"DEBUG: 'Wein' IPA: {ipa}")
        self.assertIn("aɪ̯", ipa)

    def test_syllabic_consonants(self):
        # gehen should have syllabic n [n̩]
        ipa = self.backend.get_ipa("gehen")
        print(f"DEBUG: 'gehen' IPA: {ipa}")
        self.assertIn("n̩", ipa)
        
        # Apfel should have syllabic l [l̩]
        ipa = self.backend.get_ipa("Apfel")
        print(f"DEBUG: 'Apfel' IPA: {ipa}")
        self.assertIn("l̩", ipa)

if __name__ == "__main__":
    unittest.main()
