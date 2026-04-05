from abc import ABC, abstractmethod


class Parser(ABC):
    """Abstract parser interface. Subclasses must implement parse(code) -> dict.

    Parsers MUST return the compact AST representation by default.
    """

    @abstractmethod
    def parse(self, code: str) -> dict:
        raise NotImplementedError
