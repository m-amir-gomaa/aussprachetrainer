from typing import Dict, List, Optional, Any

class TrieNode:
    __slots__ = ('children', 'lemma', 'original_casing')
    
    def __init__(self):
        self.children: Dict[str, TrieNode] = {}
        self.lemma: Optional[str] = None
        self.original_casing: Optional[str] = None

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str, lemma: Optional[str] = None):
        """
        Insert a word into the trie. 
        If lemma is provided, this node represents a valid word form pointing to that lemma.
        If lemma is None, we assume the word itself is the lemma.
        """
        node = self.root
        word_lower = word.lower()
        for char in word_lower:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        
        # If lemma is not provided, the word itself is the lemma
        node.lemma = lemma if lemma else word
        node.original_casing = word

    def search_prefix(self, prefix: str) -> List[str]:
        """
        Returns a list of lemmas for words starting with prefix.
        """
        node = self.root
        prefix_lower = prefix.lower()
        
        for char in prefix_lower:
            if char not in node.children:
                return []
            node = node.children[char]
        
        results = []
        self._collect_lemmas(node, results)
        return results

    def _collect_lemmas(self, node: TrieNode, results: List[str]):
        if node.lemma:
            # We collect the lemma, or the original word if it's the lemma
            results.append(node.lemma)
        
        # Sort keys for deterministic output
        for char in sorted(node.children.keys()):
            self._collect_lemmas(node.children[char], results)
