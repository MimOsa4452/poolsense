"""Exceptions for the PoolSense client."""


class PoolSenseError(Exception):
    """Raised when a PoolSense request ends in error.

    Attributes:
        status_code: Error code returned by the PoolSense server.
        status: More detailed description of the error.
    """

    def __init__(self, status_code: int, status: str) -> None:
        super().__init__(status)
        self.status_code = status_code
        self.status = status
