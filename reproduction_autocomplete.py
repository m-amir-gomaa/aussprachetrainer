import sys
import os
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from aussprachetrainer.autocomplete import GermanSuggester

def test_autocomplete():
    print("Initializing GermanSuggester...")
    start_time = time.time()
    suggester = GermanSuggester()
    print(f"Initialization took {time.time() - start_time:.4f}s")
    
    test_prefixes = ["geh", "kran", "ver", "haus"]
    
    for prefix in test_prefixes:
        print(f"\nSuggestions for '{prefix}':")
        start_query = time.time()
        results = suggester.suggest(prefix)
        query_time = (time.time() - start_query) * 1000
        
        for i, res in enumerate(results):
            print(f"{i+1}. {res}")
        
        print(f"Query latency: {query_time:.2f}ms")
        
        if query_time > 10:
            print("WARNING: Latency exceeded 10ms!")
        else:
            print("Latency OK (< 10ms)")

if __name__ == "__main__":
    try:
        test_autocomplete()
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
