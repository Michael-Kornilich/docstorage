from fixtures import *
from docstorage.parser import arg_parser


def test_version_with_command_exclusivity():
    with pytest.raises(SystemExit) as exc_info:
        arg_parser.parse_args("--version import".split())

    assert exc_info.value.code == 2, "The exit code should be 2"

