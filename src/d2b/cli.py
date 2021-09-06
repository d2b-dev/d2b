import argparse

from d2b.commands import create_run_parser
from d2b.d2b import __version__
from d2b.plugins import pm


def main():
    description = "d2b - Organize data in the BIDS format"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-v", "--version", action="version", version=__version__)
    subparsers = parser.add_subparsers()

    run_parser = create_run_parser(subparsers)
    pm.hook.prepare_run_parser(  # type: ignore
        parser=run_parser,
        required=run_parser._action_groups[0],
        optional=run_parser._action_groups[1],
    )

    pm.hook.register_commands(subparsers=subparsers)  # type: ignore

    args = parser.parse_args()

    if hasattr(args, "handler"):
        args.handler(args)
        return

    parser.print_help()


if __name__ == "__main__":
    exit(main())
