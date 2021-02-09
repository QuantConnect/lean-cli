class Response:
    """A Response represents an HTTP response."""

    def __init__(self, text: str, status_code: int) -> None:
        """Creates a new Response instance.

        :param text: the body of the response
        :param status_code: the status code of the response
        """
        self.text = text
        self.status_code = status_code
