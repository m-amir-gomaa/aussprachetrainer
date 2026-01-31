from aussprachetrainer.autocomplete import GermanSuggester

_suggester = None

def suggest(prefix: str):
    """
    Main API as requested: suggest(prefix: string) -> list<string>
    """
    global _suggester
    if _suggester is None:
        _suggester = GermanSuggester()
    return _suggester.suggest(prefix)
