from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

import pytest
from d2b.utils import associated_nii_ext
from d2b.utils import compare
from d2b.utils import md5
from d2b.utils import md5_from_file
from d2b.utils import md5_from_string
from d2b.utils import rsync
from pytest_mock import MockerFixture


def test_rsync(mocker: MockerFixture):
    patched_sp = mocker.patch("subprocess.run")

    rsync("a", "b")

    patched_sp.assert_called_once_with(["rsync", "-ac", "a/", "b/"], check=True)


@pytest.mark.parametrize(
    ("name", "pattern", "search_method", "case_sensitive", "expected"),
    [
        ("Test", "*es*", "fnmatch", True, True),
        ("Test", ".*es.*", "fnmatch", True, False),
        ("TEST", "*es*", "fnmatch", True, False),
        ("Test", "*ab*", "fnmatch", True, False),
        ("Test", "*es*", "fnmatch", False, True),
        ("TEST", "*es*", "fnmatch", False, True),
        ("Test", "*ab*", "fnmatch", False, False),
        ("Test", ".+es.+", "re", True, True),
        ("Test", "*es*", "re", True, False),
        ("TEST", ".+es.+", "re", True, False),
        ("Test", ".*ab.*", "re", True, False),
        ("Test", ".*es.*", "re", False, True),
        ("TEST", ".*es.*", "re", False, False),
        ("Test", ".*ab.*", "re", False, False),
    ],
)
def test_compare(
    name: str,
    pattern: str,
    search_method: str,
    case_sensitive: bool,
    expected: bool,
):
    if pattern == "*es*" and search_method == "re":
        with pytest.raises(re.error):
            compare(name, pattern, search_method, case_sensitive)
        return

    assert compare(name, pattern, search_method, case_sensitive) is expected


@pytest.mark.parametrize(
    ("files_to_create", "test_file", "expected"),
    [
        (["t.nii.gz"], "t.nii.gz", ".nii.gz"),
        (["t.nii.gz"], "t.json", ".nii.gz"),
        (["t.nii.gz"], "t", ".nii.gz"),
        (["t.nii"], "t.nii.gz", ".nii"),
        (["t.nii"], "t.json", ".nii"),
        (["t.nii"], "t", ".nii"),
        (["t.json", "t.nii.gz"], "t.nii.gz", ".nii.gz"),
        (["t.json", "t.nii.gz"], "t.json", ".nii.gz"),
        (["t.json", "t.nii.gz"], "t", ".nii.gz"),
        (["t.json", "t.nii"], "t.nii.gz", ".nii"),
        (["t.json", "t.nii"], "t.json", ".nii"),
        (["t.json", "t.nii"], "t", ".nii"),
        # non-examples
        (["a.nii.gz"], "t.nii.gz", None),
        (["a.json", "a.nii.gz"], "t.nii.gz", None),
        (["a.nii.gz"], "t.nii", None),
        (["a.json", "a.nii.gz"], "t.nii", None),
        (["a.nii.gz"], "t", None),
        (["a.json", "a.nii.gz"], "t", None),
    ],
)
def test_associated_nii_ext(
    tmpdir: str,
    files_to_create: list[str],
    test_file: str,
    expected: str | None,
):
    tmppath = Path(tmpdir)
    for fn in files_to_create:
        (tmppath / fn).write_text("")

    ext = associated_nii_ext(tmppath / test_file)

    assert expected == ext


def test_chunked_md5():
    b = BytesIO(b"Hello world")
    digest = md5(b).hexdigest()

    assert digest == "3e25960a79dbc69b674cd4ec67a72c62"


def test_md5_from_file(tmpdir: str):
    fp = Path(tmpdir) / "t.txt"
    fp.write_bytes(b"Hello world")

    digest = md5_from_file(fp).hexdigest()
    assert digest == "3e25960a79dbc69b674cd4ec67a72c62"


def test_md5_from_string():
    digest = md5_from_string("Hello world").hexdigest()
    assert digest == "3e25960a79dbc69b674cd4ec67a72c62"
