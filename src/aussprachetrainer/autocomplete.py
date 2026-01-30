import os
from typing import List

TOP_WORDS = [
    "der", "die", "das", "und", "ist", "in", "den", "von", "zu", "mit", "sich", "auf", "für", "nicht", "ein", "eine", "als", "auch", "es", "an", "werden", "aus", "er", "hat", "dass", "sie", "nach", "wird", "bei", "einer", "um", "am", "vor", "noch", "wie", "dem", "durch", "man", "nur", "einen", "sei", "sein", "war", "haben", "kann", "alle", "immer", "doch", "müssen", "würden", "können", "solche", "dieser", "ihre", "sagt", "über", "wir", "unter", "gegen", "damit", "würde", "keine", "schon", "sondern", "da", "diese", "seine", "oder", "ihr", "wollen", "geht", "jetzt", "muss", "ganz", "drei", "recht", "etwas", "dort", "vielleicht", "machte", "mensch", "leben", "zeit", "deutsch", "land", "stadt", "wo", "gut", "sehen", "sagen", "kommen", "gehen", "finden", "stehen", "lassen", "bleiben", "nehmen", "halten", "zeigen", "bringen", "fragen", "wissen", "meinen", "glauben", "denken", "ab", "aber", "allem", "allen", "aller", "alles", "also", "anderer", "anderem", "anderen", "anderes", "andere", "bin", "bis", "bist", "damit", "dann", "dein", "deine", "deinem", "deinen", "deiner", "deines", "dem", "denn", "des", "dessen", "dich", "dies", "die", "diesem", "diesen", "dieser", "dieses", "dir", "du", "einem", "einigen", "einiger", "einiges", "einmal", "euch", "euer", "eure", "eurem", "euren", "eurer", "eures", "gegen", "gewesen", "habe", "hier", "hin", "hinter", "ich", "ihm", "ihn", "ihrem", "ihren", "ihrer", "ihres", "im", "indem", "ins", "ja", "jede", "jedem", "jeden", "jeder", "jedes", "jener", "jenem", "jenen", "jenes", "kein", "keine", "keinem", "keinen", "keiner", "keines", "könnte", "machen", "manche", "manchem", "manchen", "mancher", "manches", "mein", "meine", "meinem", "meinen", "meiner", "meines", "nichts", "nun", "ob", "ohne", "sehr", "selbst", "sind", "so", "solchem", "solchen", "solcher", "solches", "soll", "sollen", "sollte", "sonst", "viel", "vom", "war", "waren", "warst", "was", "weg", "weil", "weiter", "welche", "welchem", "welchen", "welcher", "welches", "wenn", "wer", "werde", "wieder", "will", "wirst", "wollte", "während", "zwischen"
]

class WordSuggester:
    def __init__(self, history_limit: int = 1000):
        self.common_words = set()
        self.history = []
        self.history_limit = history_limit
        self.popularity_map = {word.lower(): i for i, word in enumerate(TOP_WORDS)}
        self._load_words()

    def _load_words(self):
        words_file = os.path.join(os.path.dirname(__file__), "resources", "words_de.txt")
        if os.path.exists(words_file):
            print(f"DEBUG: Loading words from {words_file}")
            try:
                with open(words_file, "r", encoding="utf-8") as f:
                    self.common_words = {line.strip() for line in f if line.strip()}
            except UnicodeDecodeError:
                print("DEBUG: UTF-8 decoding failed, falling back to latin-1")
                with open(words_file, "r", encoding="latin-1") as f:
                    # Clean words while loading
                    self.common_words = {line.strip() for line in f if line.strip() and len(line.strip()) > 1}
            print(f"DEBUG: Loaded {len(self.common_words)} words")
        else:
            self.common_words = set(TOP_WORDS)

    def add_to_history(self, word: str):
        if not word or word in self.history: return
        self.history.insert(0, word)
        if len(self.history) > self.history_limit: self.history.pop()

    def get_suggestions(self, prefix: str) -> List[str]:
        if not prefix: return []
        p_lower = prefix.lower()
        candidates = []

        # 1. From history
        for w in self.history:
            if w.lower().startswith(p_lower):
                candidates.append((w, -1)) # Highest priority

        # 2. From common words
        for w in self.common_words:
            if w.lower().startswith(p_lower):
                # Rank: TOP_WORDS index if present, else length (shorter is better), then alphabetical
                rank = self.popularity_map.get(w.lower(), 1000 + len(w))
                candidates.append((w, rank))
        
        # Sort by rank, then alphabetical
        candidates.sort(key=lambda x: (x[1], x[0].lower()))
        
        # Unique results while preserving order
        seen = set()
        results = []
        for word, _ in candidates:
            if word not in seen:
                results.append(word)
                seen.add(word)
                if len(results) >= 10: break
        return results
