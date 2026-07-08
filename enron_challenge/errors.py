"""Protocol error types for the Agent CLI Adapter."""


class ProtocolError(Exception):
    """Base class for protocol failures surfaced to the CLI."""

    exit_code = 1


class InvalidJsonError(ProtocolError):
    """Agent returned stdout that is not valid JSON."""

    exit_code = 2


class InvalidSubmissionError(ProtocolError):
    """Agent returned JSON that does not match the submission schema."""

    exit_code = 3
