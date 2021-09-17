import shutil
from pathlib import Path

import pytest


@pytest.fixture
def d2b_run_e2e(tmpdir) -> Path:
    src = Path(__file__).parent / "data/d2b_run_e2e"
    dst = Path(tmpdir) / "d2b_run_e2e"
    shutil.copytree(src, dst)
    return dst


@pytest.fixture
def scaffold_test_data(tmpdir: str) -> Path:
    src = Path(__file__).parent / "data/scaffold_test"
    dst = Path(tmpdir) / "scaffold_test"
    shutil.copytree(src, dst)
    return dst
