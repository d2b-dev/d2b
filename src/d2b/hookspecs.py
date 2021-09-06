from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING

from pluggy import HookimplMarker
from pluggy import HookspecMarker


if TYPE_CHECKING:
    from d2b.d2b import D2B
    from d2b.d2b import Acquisition


hookspec = HookspecMarker("d2b")
hookimpl = HookimplMarker("d2b")


@hookspec
def register_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register additional CLI commands, e.g. 'd2b mycommand ...'"""


@hookspec
def prepare_run_parser(
    parser: argparse.ArgumentParser,
    required: argparse._ArgumentGroup,
    optional: argparse._ArgumentGroup,
):
    """Modify the parser for the 'd2b run ...' command"""


@hookspec(firstresult=True)
def load_config(path: Path, d2b: D2B) -> dict[str, Any]:
    """Load the d2b config file"""


@hookspec
def pre_run_logs(logger: logging.Logger, d2b: D2B):
    """Write logs to the console at run start time"""


@hookspec
def collect_files(
    out_dir: Path,
    d2b_dir: Path,
    config: dict[str, Any],
    options: dict[str, Any],
    d2b: D2B,
) -> list[Path]:
    """Provide files to consider for description <-> file matching"""


@hookspec
def is_link(
    path: Path,
    criteria: dict[str, Any],
    config: dict[str, Any],
    options: dict[str, Any],
) -> bool:
    """Determine if the path matches the criteria"""


@hookspec
def pre_move(
    acquisitions: list[Acquisition],
    config: dict[str, Any],
    options: dict[str, Any],
    d2b: D2B,
):
    """Process an acquisition, after all file <-> description matches have been made,
    but before any of the files/acquisitions have been moved"""


@hookspec
def move(
    out_dir: Path,
    acquisition: Acquisition,
    acquisitions: list[Acquisition],
    config: dict[str, Any],
    options: dict[str, Any],
    d2b: D2B,
) -> list[Path]:
    """Move all files associated with this acquisition"""


@hookspec
def post_move(
    out_dir: Path,
    acquisitions: list[Acquisition],
    config: dict[str, Any],
    options: dict[str, Any],
    d2b: D2B,
):
    """Process an acquisition, after all files/acquisitions have been moved"""
