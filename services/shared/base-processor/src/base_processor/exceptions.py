"""Exception classes for base processor."""


class ProcessorException(Exception):
    """Base exception for processor errors."""

    pass


class ProcessingError(ProcessorException):
    """Error during frame processing."""

    pass


class ValidationError(ProcessorException):
    """Input validation error."""

    pass


class ResourceError(ProcessorException):
    """Resource allocation/management error."""

    pass


class InitializationError(ProcessorException):
    """Processor initialization error."""

    pass


class ResourceError(ProcessorException):
    """Resource allocation/management error."""

    pass
