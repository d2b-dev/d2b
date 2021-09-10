from __future__ import annotations

import re
import subprocess
from fnmatch import fnmatch
from pathlib import Path

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


def rsync(src: str | Path, dst: str | Path) -> Path:
    _src, _dst = Path(src), Path(dst)
    subprocess.run(["rsync", "-ac", f"{_src}/", f"{_dst}/"], check=True)
    return _dst


def compare(
    name: str,
    pattern: str,
    search_method: str = defaults.search_method,
    case_sensitive: bool = defaults.case_sensitive,
):
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
    root, _ = splitext(fp)
    niis = sorted(root.parent.glob(f"{root.stem}.nii*"))
    return niis[0] if len(niis) else None
