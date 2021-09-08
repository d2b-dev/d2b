from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING

from d2b import defaults
from d2b.hookspecs import hookimpl
from d2b.utils import compare
from d2b.utils import splitext

if TYPE_CHECKING:
    from d2b.d2b import D2B
    from d2b.d2b import Acquisition


@hookimpl
def load_config(path: Path):
    if not path.suffix == ".json":
        # if it's not a json config file let someone else handle it
        return
    return json.loads(path.read_text())


@hookimpl
def collect_files(d2b_dir: Path) -> list[Path]:
    return list(d2b_dir.rglob("*.json"))


@hookimpl
def is_link(
    path: Path,
    criteria: dict[str, Any],
    config: dict[str, Any],
):
    _, ext = splitext(path)
    if ext != ".json":
        # if it's not a sidecar file let someone else handle it
        return

    data = json.loads(path.read_text())
    search_method = config.get("searchMethod", defaults.search_method)
    case_sensitive = config.get("caseSensitive", defaults.case_sensitive)

    result: list[bool] = []
    for tag, pattern in criteria.items():
        tagValue = data.get(tag, "")

        if tag == "filename" or tag == "SidecarFilename":
            # check the file name of the sidecar
            result.append(compare(path.name, pattern, search_method, case_sensitive))

        elif isinstance(tagValue, list) and isinstance(pattern, list):
            # check that there's a bijective mapping between the two lists
            matching_length = len(tagValue) == len(pattern)
            matching_contents = all(
                [
                    any(
                        compare(tagItem, patternItem, search_method, case_sensitive)
                        for tagItem in tagValue
                    )
                    for patternItem in pattern
                ],
            )
            result.append(matching_length and matching_contents)

        else:
            # check the value
            result.append(
                compare(str(tagValue), pattern, search_method, case_sensitive),
            )

    return all(result)


@hookimpl
def move(out_dir: Path, acquisition: Acquisition, d2b: D2B):
    from d2b.d2b import __version__

    if acquisition.src_file.suffix != ".json":
        # if the file that was the source of this acq wasn't a json file
        # (hopefully this is synonymous with it being a sidecar in most
        # occasions) then bail early, we aren't going to pretend to
        # know how to handle "non-sidecar-based" acquisitions.
        return

    src_parent = acquisition.src_root.parent
    src_stem = acquisition.src_root.name
    src_files = [fp for fp in src_parent.rglob(f"{src_stem}.*") if fp.is_file()]

    dst_files: list[Path] = []
    for src in src_files:
        _, ext = splitext(src)
        dst = out_dir / acquisition.dst_root.with_suffix(ext)
        dst.parent.mkdir(exist_ok=True, parents=True)
        d2b.logger.info(f"Moving [{src}] -> [{dst}]")

        if ext != ".json":
            # if it's not the sidecar, just copy it over
            os.rename(src, dst)

        else:
            # load + apply sidecarChanges + (optionally) add IntendedFor
            data = json.loads(src.read_text())
            data = {
                **data,
                **acquisition.description.sidecar_changes,
                "D2bVersion": __version__,
            }
            intended_for = acquisition.data.get("IntendedFor")
            if intended_for is not None:
                data["IntendedFor"] = intended_for
            # write the file
            dst.write_text(json.dumps(data, indent=2))
            # remove src
            os.remove(src)

        dst_files.append(dst)

    return dst_files
