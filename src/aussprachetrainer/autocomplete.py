import os
import math
from typing import List, Set, Dict, Optional
from aussprachetrainer.trie import Trie
from aussprachetrainer.hunspell_wrapper import HunspellWrapper
from aussprachetrainer.ranking import RankingEngine
from aussprachetrainer.text_engine_wrapper import TextEngine

class GermanSuggester:
    def __init__(self, history_limit: int = 1000):
        self.resources_dir = os.path.join(os.path.dirname(__file__), "resources")
        self.dict_dir = os.path.join(self.resources_dir, "dicts")
        
        # Paths
        dic_path = os.path.join(self.dict_dir, "de_DE.dic")
        aff_path = os.path.join(self.dict_dir, "de_DE.aff")
        freq_path = os.path.join(self.resources_dir, "top10000de.txt")
        history_path = os.path.join(self.resources_dir, "user_history_de.txt")
        
        # Components
        self.trie_py = Trie() 
        self.text_engine = TextEngine()
        self.hunspell = HunspellWrapper(dic_path, aff_path)
        self.ranking = RankingEngine(freq_path)
        
        self.history: Set[str] = set()
        self.history_limit = history_limit
        self.history_path = history_path
        
        self._load_dictionary(dic_path)
        self._load_history()

    def _load_dictionary(self, dic_path: str):
        if not os.path.exists(dic_path): return
        
        try:
            with open(dic_path, "r", encoding="utf-8", errors="ignore") as f:
                next(f, None)
                for line in f:
                    parts = line.strip().split('/')
                    word = parts[0]
                    if word and len(word) > 1:
                        rank = self.ranking.frequencies.get(word.lower(), 10000)
                        frequency_score = math.log((10001 - rank) + 1)
                        
                        self.trie_py.insert(word)
                        self.text_engine.insert_word(word, frequency_score)
        except Exception as e:
            print(f"DEBUG: Error loading dictionary: {e}")

    def _load_history(self):
        if not os.path.exists(self.history_path): return
        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                for line in f:
                    word = line.strip()
                    if word:
                        self.history.add(word)
                        self.text_engine.insert_word(word, 100.0) # High priority
        except Exception as e:
            print(f"DEBUG: Error loading history: {e}")

    def add_to_history(self, word: str):
        if not word or word in self.history: return
        self.history.add(word)
        self.text_engine.insert_word(word, 100.0)
        try:
            with open(self.history_path, "a", encoding="utf-8") as f:
                f.write(word + "\n")
        except: pass

    def suggest(self, prefix: str) -> List[str]:
        return self.get_suggestions(prefix)

    def get_suggestions(self, prefix: str) -> List[str]:
        if not prefix: return []
        p_lower = prefix.lower()
        
        # 1. High Performance Path (C Engine)
        if self.text_engine.is_available():
            return self.text_engine.search_ranked(p_lower)
        
        # 2. Fallback Path (Python)
        candidates: List[tuple[str, float]] = []
        seen_words: Set[str] = set()
        
        lemmas = self.trie_py.search_prefix(p_lower)
        for lemma in lemmas:
            forms = self.hunspell.expand_lemma(lemma)
            for word in forms:
                if word.lower().startswith(p_lower) and word not in seen_words:
                    score = self.ranking.score(word, prefix, is_lemma=(word == lemma), is_history=(word in self.history))
                    candidates.append((word, score))
                    seen_words.add(word)
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [c[0] for c in candidates[:10]]

# Backward compatibility
WordSuggester = GermanSuggester
