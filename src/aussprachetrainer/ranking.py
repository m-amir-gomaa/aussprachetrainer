import math
import os
from typing import Dict, List, Optional

class RankingEngine:
    def __init__(self, frequency_file: Optional[str] = None):
        self.frequencies: Dict[str, int] = {}
        if frequency_file:
            self._load_frequencies(frequency_file)

    def _load_frequencies(self, path: str):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        word = line.strip().lower()
                        if word and word not in self.frequencies:
                            self.frequencies[word] = i # Rank (Lower is more frequent)
        except Exception as e:
            print(f"Error loading frequencies: {e}")

    def score(self, word: str, prefix: str, is_compound: bool = False, is_lemma: bool = False, is_history: bool = False) -> float:
        # Specified score example:
        # score = (prefix_length * 10) + log(frequency + 1) - compound_penalty + user_bonus
        
        # 1. Prefix length boost
        score = len(prefix) * 10.0
        
        # 2. Frequency (we use rank as proxy if frequency is unknown)
        # Assuming max rank 10000, frequency = 10001 - rank
        rank = self.frequencies.get(word.lower(), 10000)
        frequency = 10001 - rank
        score += math.log(frequency + 1)
        
        # 3. Morphological simplicity (slight boost for base forms)
        if is_lemma:
            score += 2.0
            
        # 4. User history bonus
        if is_history:
            score += 15.0
            
        # 5. Compound penalty
        if is_compound:
            score -= 5.0
            if len(word) > 15:
                score -= 5.0  # Extra penalty for very long compounds
                
        return score
