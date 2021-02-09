import sys
import traceback

from lean.commands import lean
from lean.container import container


def main() -> None:
    """This function is the entrypoint when running a Lean command in a terminal."""
    try:
        lean.main()
    except Exception as exception:
        logger = container.logger()

        logger.debug(traceback.print_exc())
        logger.error(f"Error: {exception}")

        sys.exit(1)
