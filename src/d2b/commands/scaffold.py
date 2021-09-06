import argparse
import datetime
import shutil
from pathlib import Path
from typing import List
from typing import Union

from d2b.hookspecs import hookimpl


@hookimpl
def register_commands(subparsers: argparse._SubParsersAction):
    create_scaffold_parser(subparsers)


def create_scaffold_parser(subparsers: Union[argparse._SubParsersAction, None]):
    description = "Scaffold a BIDS dataset directory structure"
    if subparsers is None:
        _parser = argparse.ArgumentParser(description=description)
    else:
        _parser = subparsers.add_parser("scaffold", description=description)

    _parser.add_argument(
        "out_dir",
        type=Path,
        help="Output BIDS directory",
    )

    _parser.set_defaults(handler=handler)

    return _parser


def handler(args: argparse.Namespace):
    out_dir: Path = args.out_dir

    # create the directories required by BIDS
    for d in _get_scaffold_bids_dirnames():
        (out_dir / d).mkdir(exist_ok=True)

    # create the files required by BIDS
    for f in _get_scaffold_bids_filenames():
        shutil.copyfile(_get_scaffold_template_dir() / f, out_dir / f)

    # create + modify the CHANGES file
    changes_file = _get_scaffold_template_dir() / "CHANGES"
    data = changes_file.read_text().format(datetime.date.today().strftime("%Y-%m-%d"))
    (out_dir / changes_file.name).write_text(data)


def _get_scaffold_bids_dirnames() -> List[str]:
    return ["code", "derivatives", "sourcedata"]


def _get_scaffold_bids_filenames() -> List[str]:
    f = [
        "dataset_description.json",
        "participants.json",
        "participants.tsv",
        "README",
        ".bidsignore",
    ]
    return f


def _get_scaffold_template_dir() -> Path:
    return Path(__file__).parent / "scaffold_template"
