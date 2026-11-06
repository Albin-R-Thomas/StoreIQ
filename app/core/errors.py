class IntegrationNotConfigured(Exception):
    """An optional adapter has not been configured."""


class IntegrationFailure(Exception):
    """An upstream failed; do not leak provider payloads or credentials."""
