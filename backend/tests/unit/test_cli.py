import subprocess
import sys


def test_cli_loads_complete_model_registry() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.cli import User; from sqlalchemy.orm import configure_mappers; configure_mappers()",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
