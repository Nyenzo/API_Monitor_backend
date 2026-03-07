from fastapi import HTTPException, status


# Raised when a requested resource does not exist in the database
class NotFoundError(HTTPException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found",
        )


# Raised when an authenticated user tries to access a resource they do not own
class ForbiddenError(HTTPException):
    def __init__(self, detail: str = "You do not have access to this resource"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


# Raised when creating a resource that already exists
class ConflictError(HTTPException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


# Raised when request input fails validation not covered by Pydantic
class BadRequestError(HTTPException):
    def __init__(self, detail: str = "Invalid request"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


# Raised when an external dependency like Supabase is unreachable
class ServiceUnavailableError(HTTPException):
    def __init__(self, detail: str = "Service temporarily unavailable"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
