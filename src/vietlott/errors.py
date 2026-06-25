class FetchError(Exception):
    """Raised when fetching a vietlott.vn page fails."""


class ParseError(Exception):
    """Raised when the fetched HTML can't be parsed into DrawResults."""
