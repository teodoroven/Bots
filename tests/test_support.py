from __future__ import annotations

import shutil
from uuid import uuid4
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
TEMP_ROOT: Path = ROOT / ".test_tmp"


class WorkspaceTemporaryDirectory:

    def __init__(self):
        TEMP_ROOT.mkdir(exist_ok = True)
        self.name: str = str(TEMP_ROOT / uuid4().hex)

    def __enter__(self) -> str:
        Path(self.name).mkdir(parents = True, exist_ok = False)
        return self.name

    def __exit__(self, exc_type: object, exc_value: object, traceback: object):
        shutil.rmtree(self.name, ignore_errors = True)


def temp_directory() -> WorkspaceTemporaryDirectory:
    TEMP_ROOT.mkdir(exist_ok = True)
    return WorkspaceTemporaryDirectory()
