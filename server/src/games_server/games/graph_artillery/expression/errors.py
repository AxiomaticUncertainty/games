class ParseError(ValueError):
    """The text isn't a valid expression.

    `message` is written for players. `position` is the index of the character
    where the problem was found, so the UI can point at it.
    """

    def __init__(self, message: str, position: int) -> None:
        super().__init__(message)
        self.message = message
        self.position = position
