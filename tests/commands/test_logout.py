from click.testing import CliRunner

from lean.commands import lean
from tests.test_helpers import MockContainer


def test_logout_should_clear_credentials_storage(mock_container: MockContainer) -> None:
    result = CliRunner().invoke(lean, ["logout"])

    assert result.exit_code == 0

    mock_container.credentials_storage_mock.clear.assert_called()
