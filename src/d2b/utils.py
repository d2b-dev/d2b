from __future__ import annotations

import hashlib
import re
import subprocess
from fnmatch import fnmatch
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from d2b import defaults


def splitext(
    path: str | Path,
    custom_extensions: list[str] = None,
) -> tuple[Path, str]:
    """Split the extension from a pathname.

    Examples:
        >>> splitext('a/b.json')
        (PosixPath('a/b'), '.json')
        >>> #
        >>> splitext('a/b.nii.gz')
        (PosixPath('a/b'), '.nii.gz')
        >>> #
        >>> splitext('a/b.tar.gz')
        (PosixPath('a/b.tar'), '.gz')
        >>> #
        >>> splitext('a/b.tar.gz', ['.tar.gz'])
        (PosixPath('a/b'), '.tar.gz')
    """
    _extensions = custom_extensions or [".nii.gz"]

    for ext in _extensions:
        s = str(path)
        if s.endswith(ext):
            return Path(s[: -len(ext)]), s[-len(ext) :]  # noqa: E203

    p = Path(path)
    return p.parent / p.stem, p.suffix


def prepend(value: str, char="_"):
    """Prepend a string to a value if the value doesn't already start with that string

    Examples:
        >>> prepend('a')
        '_a'
        >>> prepend('_a')
        '_a'
        >>> prepend('my_str', '--')
        '--my_str'
        >>> prepend('---my_str', '-')
        '---my_str'
    """
    if value.strip() == "":
        return ""
    return value if value.startswith(char) else f"{char}{value}"


def rsync(src: str | Path, dst: str | Path, delete: bool = False) -> Path:
    """Thin wrapper around the 'rsync' command line tool.

    Args:
        src (str | Path): The source directory to synchronize.
        dst (str | Path): The destination directory to synchronize to.
        delete (bool): Whether to delete extraneous files from the
            receiving side (`dst`) (default: False)
    """
    _src, _dst = Path(src), Path(dst)
    cmd = ("rsync", "-ac")
    if delete:
        cmd += ("--delete",)
    cmd += (f"{_src}/", f"{_dst}/")
    subprocess.run(cmd, check=True)
    return _dst


def compare(
    name: str,
    pattern: str,
    search_method: str = defaults.search_method,
    case_sensitive: bool = defaults.case_sensitive,
) -> bool:
    """Determine if a string matches a pattern.

    Args:
        name (str): The string to test.
        pattern (str): The pattern to search for.
        search_method (str, optional): How to interpret name, one of
            `fnmatch` (default) or `re`. Defaults to defaults.search_method.
        case_sensitive (bool, optional): Whether the search is performed in
            a case-sensitive manner, if `search_method` is `re` then this
            parameter is ignored. Defaults to defaults.case_sensitive.

    Returns:
        bool: Whether `name` is a match for `pattern`
    """
    name, pattern = str(name), str(pattern)
    if search_method == "re":
        return bool(re.search(pattern, name))
    elif case_sensitive:
        return fnmatch(name, pattern)
    else:
        return fnmatch(name.lower(), pattern.lower())


def associated_nii_ext(fp: str | Path) -> str | None:
    """Returns .nii, .nii.gz, or None.

    The suffix returned matches the first file found which shares a
    file root (parent dir + stem) with `fp`. `None` is returned if no
    matching nii file is found.
    """
    nii = first_nii(fp)
    if nii is None:
        return
    _, ext = splitext(nii)
    return ext


def first_nii(fp: str | Path) -> Path | None:
    """Returns the first .nii[.gz] file found which shares a stem with `fp`

    Examples:
        >>> import contextlib, tempfile
        >>> from pathlib import Path
        >>> # --- a helper function
        >>> @contextlib.contextmanager
        ... def preloaded_tempdir(files, **kwargs):
        ...     with tempfile.TemporaryDirectory(**kwargs) as d:
        ...         for fn in files:
        ...             _ = (Path(d) / fn).write_text('')
        ...         yield Path(d)
        ...
        >>>
        >>> # --- gzipped nii files
        >>> files = ['a.json', 'a.nii.gz', 'b.nii.gz']
        >>> with preloaded_tempdir(files, suffix='my_test_dir') as d:
        ...     nii_file = first_nii(d / 'a.json')
        ...
        >>> print(nii_file.name)
        a.nii.gz
        >>>
        >>> # --- non-gzipped nii files
        >>> files = ['a.json', 'a.nii', 'b.nii']
        >>> with preloaded_tempdir(files, suffix='my_test_dir') as d:
        ...     nii_file = first_nii(d / 'a.json')
        ...
        >>> print(nii_file.name)
        a.nii
        >>>
        >>> # --- no match
        >>> files = ['a.json', 'a.txt', 'b.txt']
        >>> with preloaded_tempdir(files, suffix='my_test_dir') as d:
        ...     nii_file = first_nii(d / 'a.json')
        ...
        >>> print(nii_file)
        None
    """
    root, _ = splitext(fp)
    niis = sorted(root.parent.glob(f"{root.stem}.nii*"))
    return niis[0] if len(niis) else None


def md5(f: BinaryIO) -> hashlib._Hash:
    md5_hash = hashlib.md5()
    for byte_block in iter(lambda: f.read(4096), b""):
        md5_hash.update(byte_block)
    return md5_hash


def md5_from_file(fp: str | Path) -> hashlib._Hash:
    with open(fp, "rb") as f:
        return md5(f)


def md5_from_string(s: str) -> hashlib._Hash:
    b = BytesIO(s.encode("utf8"))
    return md5(b)
