import os
import sys
from typing import List, Set, Optional

# Try importing phunspell
try:
    import phunspell # type: ignore
except ImportError:
    phunspell = None

class HunspellWrapper:
    def __init__(self, dic_path: str, aff_path: str):
        self.dict_path = dic_path
        self.aff_path = aff_path
        self.ps = None
        
        # Phunspell expects a directory and a language name
        self.dict_dir = os.path.dirname(dic_path)
        self.lang = os.path.basename(dic_path).split('.')[0] # e.g. 'de_DE'
        
        if not os.path.exists(dic_path) or not os.path.exists(aff_path):
            print(f"ERROR: Hunspell files not found: {dic_path}, {aff_path}", file=sys.stderr)
            return

        if phunspell:
            try:
                # Phunspell looks in standard directories. 
                # We might need to point it to our resources/dicts if it doesn't find it.
                # However, usually we can initialize it with the language code if dicts are installed.
                # Since we have the dicts in resources, we might need a workaround if phunspell doesn't take paths.
                self.ps = phunspell.Phunspell(self.lang)
            except Exception as e:
                print(f"WARNING: Failed to initialize Phunspell: {e}. Attempting limited mode.", file=sys.stderr)
        else:
            print("WARNING: phunspell module not found. Autocomplete will be limited.", file=sys.stderr)

    def is_valid(self, word: str) -> bool:
        if not self.ps:
            return True # Fail open
        try:
            return self.ps.lookup(word)
        except:
            return False

    def suggest(self, word: str) -> List[str]:
        if not self.ps:
            return []
        try:
            return list(self.ps.suggest(word))
        except:
            return []

    def get_stems(self, word: str) -> List[str]:
        # Phunspell doesn't have a direct stem() method like cyhunspell
        return [word]
            
    def analyze(self, word: str) -> List[str]:
        return []

    def expand_lemma(self, lemma: str) -> List[str]:
        """
        Generate inflected forms. Phunspell doesn't support this directly.
        We'll rely on suggest() and Trie loading.
        """
        return [lemma]

    def is_compound(self, word: str) -> bool:
        if not self.ps:
            return False
        return len(word) > 12 and self.ps.lookup(word)

    def split_compound(self, word: str, min_len: int = 4) -> List[str]:
        if not self.ps or not word:
            return []
        
        length = len(word)
        if length < min_len * 2:
            return [word] if self.is_valid(word) else []

        for i in range(min_len, length - min_len + 1):
            left = word[:i]
            right = word[i:]
            if self.is_valid(left):
                if self.is_valid(right):
                    return [left, right]
                rest = self.split_compound(right)
                if rest:
                    return [left] + rest
        
        return [word] if self.is_valid(word) else []
