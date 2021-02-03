import click


class FailedRequestException(click.ClickException):
    """An error indicating that a request has failed."""

    def __init__(self, message: str) -> None:
        super(FailedRequestException, self).__init__(message)


class AuthenticationException(FailedRequestException):
    """An error indicating that a request has failed because the used credentials were invalid."""

    def __init__(self) -> None:
        super(AuthenticationException, self).__init__("Invalid credentials, please log in using `lean login`")
