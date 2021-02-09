from lean.models.response import Response


class RequestFailedError(Exception):
    """A RequestFailedError indicates that an HTTP request has failed."""

    def __init__(self, message: str, response: Response) -> None:
        """Creates a new RequestFailedError instance.

        :param message: a descriptive and display-friendly error message
        :param response: the data of the failed response
        """
        super().__init__(message)

        self.response = response


class AuthenticationError(Exception):
    """An error indicating that a request has failed because the used credentials were invalid."""

    def __init__(self) -> None:
        super().__init__("Invalid credentials, please log in using `lean login`")
