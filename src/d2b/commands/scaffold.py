from __future__ import annotations

import argparse
import datetime
import shutil
from pathlib import Path

from d2b.hookspecs import hookimpl
from d2b.scaffold import DatasetDescription


@hookimpl
def register_commands(subparsers: argparse._SubParsersAction):
    create_scaffold_parser(subparsers)


def create_scaffold_parser(subparsers: argparse._SubParsersAction | None):
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

    # dataset description options
    dataset_description_group = _parser.add_argument_group(
        "dataset description parameters",
    )
    dataset_description_group.add_argument(
        "--name",
        dest="Name",
        default="",
        help="The Name field.",
    )
    dataset_description_group.add_argument(
        "--bids-version",
        dest="BIDSVersion",
        default="",
        help="The BIDSVersion field.",
    )
    dataset_description_group.add_argument(
        "--dataset-type",
        dest="DatasetType",
        choices=("raw", "derived"),
        default="raw",
        help="The DatasetType field.",
    )
    dataset_description_group.add_argument(
        "--license",
        dest="License",
        default="",
        help="The License field.",
    )
    dataset_description_group.add_argument(
        "--authors",
        dest="Authors",
        action="append",
        # default=[""],
        help="The Authors field. This flag can be specified multiple times.",
    )
    dataset_description_group.add_argument(
        "--acknowledgements",
        dest="Acknowledgements",
        default="",
        help="The Acknowledgements field.",
    )
    dataset_description_group.add_argument(
        "--how-to-acknowledge",
        dest="HowToAcknowledge",
        default="",
        help="The HowToAcknowledge field.",
    )
    dataset_description_group.add_argument(
        "--funding",
        dest="Funding",
        action="append",
        # default=[""],
        help="The Funding field. This fag can be specified multiple times.",
    )
    dataset_description_group.add_argument(
        "--ethics-approvals",
        dest="EthicsApprovals",
        action="append",
        # default=[""],
        help="The EthicsApprovals field. This fag can be specified multiple times.",
    )
    dataset_description_group.add_argument(
        "--references-and-links",
        dest="ReferencesAndLinks",
        action="append",
        # default=[""],
        help="The ReferencesAndLinks field. This fag can be specified multiple times.",
    )
    dataset_description_group.add_argument(
        "--dataset-doi",
        dest="DatasetDOI",
        default="",
        help="The DatasetDOI field.",
    )
    dataset_description_group.add_argument(
        "--hed-version",
        dest="HEDVersion",
        default="",
        help="The HEDVersion field.",
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

    # create the dataset_description.json file
    description_file = DatasetDescription.from_dict(vars(args))
    description_file.to_filename(out_dir / "dataset_description.json")


def _get_scaffold_bids_dirnames() -> list[str]:
    return ["code", "derivatives", "sourcedata"]


def _get_scaffold_bids_filenames() -> list[str]:
    f = [
        "participants.json",
        "participants.tsv",
        "README",
        ".bidsignore",
    ]
    return f


def _get_scaffold_template_dir() -> Path:
    return Path(__file__).parent / "scaffold_template"
