"""Domain errors. API layer maps them to HTTP responses in app.main."""


class AppError(Exception):
    status_code: int = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404


class ForbiddenError(AppError):
    status_code = 403


class ConflictError(AppError):
    status_code = 409


class ValidationError(AppError):
    status_code = 422


class KeitaroError(AppError):
    """Keitaro API failed or answered with an error."""

    status_code = 502

    def __init__(self, message: str, upstream_status: int | None = None, payload: object = None):
        super().__init__(message)
        self.upstream_status = upstream_status
        self.payload = payload
