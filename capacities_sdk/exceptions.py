"""Custom exceptions for Capacities SDK."""


class CapacitiesError(Exception):
    """Base exception for Capacities SDK."""

    def __init__(self, message: str, status_code: int = None, response: dict = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class AuthenticationError(CapacitiesError):
    """Raised when authentication fails."""

    pass


class RateLimitError(CapacitiesError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: int = None,
        status_code: int = 429,
        response: dict = None,
    ):
        self.retry_after = retry_after
        super().__init__(message, status_code, response)


class NotFoundError(CapacitiesError):
    """Raised when a resource is not found."""

    pass


class ValidationError(CapacitiesError):
    """Raised when input validation fails."""

    pass


class SyncError(CapacitiesError):
    """Raised when sync operations fail."""

    pass
