import argparse
from pathlib import Path
from typing import Union

from d2b import defaults
from d2b.d2b import D2B


def create_run_parser(subparsers: Union[argparse._SubParsersAction, None]):
    description = "Organize data in the BIDS format"
    if subparsers is None:
        _parser = argparse.ArgumentParser(description=description)
    else:
        _parser = subparsers.add_parser("run", description=description)

    _parser._action_groups.pop()
    required = _parser.add_argument_group("required arguments")
    optional = _parser.add_argument_group("optional arguments")

    _parser.add_argument(
        "in_dir",
        type=Path,
        nargs="+",
        help="Directory(ies) containing files to organize",
    )

    required.add_argument(
        "-c",
        "--config",
        dest="config_file",
        type=Path,
        required=True,
        help="JSON configuration file (see example/config.json)",
    )
    required.add_argument("-p", "--participant", required=True, help="Participant ID")
    required.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        required=True,
        help="Output BIDS directory",
    )

    optional.add_argument(
        "-s",
        "--session",
        default=defaults.cli_session,
        help="Session ID",
    )
    optional.add_argument(
        "-l",
        "--log-level",
        default=defaults.cli_log_level,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level",
    )

    _parser.set_defaults(handler=handler)

    return _parser


def handler(args: argparse.Namespace):
    app = D2B(
        in_dirs=args.in_dir,
        out_dir=args.out_dir,
        config_file=args.config_file,
        participant=args.participant,
        session=args.session,
        options=vars(args),
    )
    app.load_config()
    return app.run()
