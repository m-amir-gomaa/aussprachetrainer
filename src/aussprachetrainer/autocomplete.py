import os
from typing import List

class WordSuggester:
    def __init__(self, history_limit: int = 1000):
        self.common_words = set()
        self.history = []
        self.history_limit = history_limit
        
        # Load words from resources if available
        self._load_words()

    def _load_words(self):
        # We'll use a local file for the 100k words
        # For now, we populate with a reasonable set and allow it to grow
        # In a real app, we'd bundle a 1-2MB text file.
        words_file = os.path.join(os.path.dirname(__file__), "resources", "words_de.txt")
        if os.path.exists(words_file):
            with open(words_file, "r", encoding="utf-8") as f:
                self.common_words = {line.strip() for line in f if line.strip()}
        else:
            # Fallback/Starter words
            self.common_words = {
                "Hallo", "Guten", "Tag", "Morgen", "Abend", "Danke", "Bitte", "Ja", "Nein",
                "sprechen", "lernen", "deutsch", "Aussprache"
            }

    def add_to_history(self, word: str):
        if not word or word in self.history:
            return
        self.history.insert(0, word)
        if len(self.history) > self.history_limit:
            self.history.pop()

    def get_suggestions(self, prefix: str) -> List[str]:
        if not prefix or len(prefix) < 1:
            return []
        
        prefix_lower = prefix.lower()
        suggestions = []
        
        # 1. Check history first
        for word in self.history:
            if word.lower().startswith(prefix_lower):
                suggestions.append(word)
                if len(suggestions) >= 10: return suggestions
        
        # 2. Check common words
        # For 100k words, we might want a prefix tree (trie), but a simple
        # prefix check on a set is actually okay for 100k if we don't do it 
        # on every single character change in a blocking way.
        for word in self.common_words:
            if word.lower().startswith(prefix_lower) and word not in self.history:
                suggestions.append(word)
                if len(suggestions) >= 10:
                    break
                    
        return suggestions
