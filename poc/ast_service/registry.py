from typing import Dict, Optional


class LanguageRegistry:
    def __init__(self):
        self._parsers: Dict[str, object] = {}

    def register(self, name: str, parser: object) -> None:
        """Register a parser instance for a language name."""
        self._parsers[name.lower()] = parser

    def get(self, name: str) -> Optional[object]:
        return self._parsers.get(name.lower())


registry = LanguageRegistry()
