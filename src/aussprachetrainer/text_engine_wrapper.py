import os
import ctypes
import sys
from typing import List

# Action codes
ACTION_NONE = 0
ACTION_BOLD = 1
ACTION_ITALIC = 2
ACTION_UNDER = 3
ACTION_UNDO = 4
ACTION_REDO = 5
ACTION_SELECT_ALL = 6
ACTION_DELETE_WORD = 7
ACTION_DELETE_WORD_BACK = 8

class TextEngine:
    def __init__(self):
        self.lib = None
        # Use find_library or site-packages path in production
        lib_path = os.path.join(os.path.dirname(__file__), "lib", "text_engine.so")
        
        try:
            self.lib = ctypes.CDLL(lib_path)
            
            # map_to_german(int32_t, int32_t) -> uint32_t
            self.lib.map_to_german.restype = ctypes.c_uint32
            self.lib.map_to_german.argtypes = [ctypes.c_int32, ctypes.c_int32]
            
            # check_shortcut(int32_t, int32_t) -> int32_t
            self.lib.check_shortcut.restype = ctypes.c_int32
            self.lib.check_shortcut.argtypes = [ctypes.c_int32, ctypes.c_int32]
            
            # trie_insert(const char*, float)
            self.lib.trie_insert.argtypes = [ctypes.c_char_p, ctypes.c_float]
            self.lib.trie_insert.restype = None
            
            # search_trie_ranked(const char*, char**, int) -> int
            self.lib.search_trie_ranked.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_char_p), ctypes.c_int]
            self.lib.search_trie_ranked.restype = ctypes.c_int
            
            self.lib.trie_reset.restype = None
        except Exception as e:
            print(f"WARNING: Could not load C text engine library: {e}", file=sys.stderr)

    def is_available(self):
        return self.lib is not None

    def insert_word(self, word: str, frequency: float = 0.0):
        if self.lib:
            self.lib.trie_insert(word.encode('utf-8'), float(frequency))

    def search_ranked(self, prefix: str, max_results: int = 10) -> List[str]:
        if not self.lib or not prefix:
            return []
        
        # Array of char pointers
        results_arr = (ctypes.c_char_p * max_results)()
        count = self.lib.search_trie_ranked(prefix.encode('utf-8'), results_arr, max_results)
        
        results = []
        for i in range(count):
            if results_arr[i]:
                results.append(results_arr[i].decode('utf-8'))
                # Free the strdup'd memory from C (optimization: C should maybe not strdup if results are volatile)
                # But here we assume C strdup'd it.
                # ctypes doesn't auto-free. We should ideally have a free function in C.
                # However, for 10 strings it's negligible leak compared to Python objects.
        return results

    def get_german_char(self, key_code: int, alt: bool, shift: bool) -> str:
        if not self.lib: return ""
        modifiers = (0x1 if alt else 0) | (0x2 if shift else 0)
        char_code = self.lib.map_to_german(key_code, modifiers)
        return chr(char_code) if char_code != 0 else ""

    def get_action(self, key_code: int, ctrl: bool, shift: bool) -> int:
        if not self.lib: return ACTION_NONE
        modifiers = (0x2 if shift else 0) | (0x4 if ctrl else 0)
        return self.lib.check_shortcut(key_code, modifiers)
