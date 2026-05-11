from __future__ import annotations

from pathlib import Path

project_package: Path = Path(__file__).resolve().parents[2] / "bots"
project_init: Path = project_package / "__init__.py"

__path__.append(str(project_package))
exec(compile(project_init.read_text(encoding = "utf-8"), str(project_init), "exec"), globals())
