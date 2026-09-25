"""Explicit error types. Each carries an HTTP status so the API layer can map them without guessing."""


class PhotoGenError(Exception):
    http_status = 500
    code = "internal_error"

    def __init__(self, message: str, **details):
        super().__init__(message)
        self.message = message
        self.details = details

    def to_dict(self) -> dict:
        return {"error": self.code, "message": self.message, **({"details": self.details} if self.details else {})}


class ConfigError(PhotoGenError):
    code = "config_error"


class ValidationError(PhotoGenError):
    http_status = 400
    code = "invalid_request"


class UnsupportedParameterError(ValidationError):
    code = "unsupported_parameter"


class QueueFullError(PhotoGenError):
    http_status = 429
    code = "queue_full"


class NotFoundError(PhotoGenError):
    http_status = 404
    code = "not_found"


class ConflictError(PhotoGenError):
    http_status = 409
    code = "conflict"


class RuntimeUnavailableError(PhotoGenError):
    """Runtime environment missing, version drift, or model integrity failure. Never auto-repaired."""
    http_status = 503
    code = "runtime_unavailable"


class GenerationError(PhotoGenError):
    code = "generation_failed"


class OutputCorruptedError(GenerationError):
    code = "output_corrupted"


class JobCancelledError(PhotoGenError):
    code = "cancelled"
