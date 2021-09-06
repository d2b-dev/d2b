# d2b

Organize data in the BIDS format.

[![PyPI Version](https://img.shields.io/pypi/v/d2b.svg)](https://pypi.org/project/d2b/)

Compatible with `dcm2bids` config files.

## Installation

```bash
pip install d2b
```

## Usage

The singular CLI entrypoint:

```bash
$ d2b --help
usage: d2b [-h] [-v] {run,scaffold} ...

d2b - Organize data in the BIDS format

positional arguments:
  {run,scaffold}

optional arguments:
  -h, --help      show this help message and exit
  -v, --version   show program's version number and exit
```

Scaffold a BIDS dataset:

```bash
$ d2b scaffold --help
usage: d2b scaffold [-h] out_dir

Scaffold a BIDS dataset directory structure

positional arguments:
  out_dir     Output BIDS directory

optional arguments:
  -h, --help  show this help message and exit
```

Organize nifti data (sidecars required) into a BIDS-compliant structure:

```bash
$ d2b run --help
usage: d2b run [-h] -c CONFIG_FILE -p PARTICIPANT -o OUT_DIR [-s SESSION] [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}] in_dir [in_dir ...]

Organize data in the BIDS format

positional arguments:
  in_dir                Directory(ies) containing files to organize

required arguments:
  -c CONFIG_FILE, --config CONFIG_FILE
                        JSON configuration file (see example/config.json)
  -p PARTICIPANT, --participant PARTICIPANT
                        Participant ID
  -o OUT_DIR, --out-dir OUT_DIR
                        Output BIDS directory

optional arguments:
  -s SESSION, --session SESSION
                        Session ID
  -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set logging level
```

## Motivation

This package offers a pluggable BIDS-ification workflow which attempts to mirror parts of the [`dcm2bids`](https://github.com/UNFmontreal/Dcm2Bids) CLI.

**This most important goal of this package is to support existing `dcm2bids` config files.**

A notable difference between `d2b` and `dcm2bids` is that the default assumption made by `d2b` is that you're **_NOT_** giving it DICOM data as input (although, if this is your use-case, there's a plugin to enable going straight from DICOM -> BIDS).

Out of the box, `d2b` assumes that you're working with NIfTI + NIfTI sidecar data.

The general premise of the `dcm2bids` workflow is very nice: _describe the files your interested in (in config) and the software will take the descriptions, find matching files, and organize those files accordingly_.

`d2b` (together with plugins powered by [`pluggy`](https://github.com/pytest-dev/pluggy)) tries to offer all functionality that `dcm2bids` offers, with an aim toward being _extensible_.

We wanted `dcm2bids` to do things that it was [never intended to do](https://github.com/UNFmontreal/Dcm2Bids/issues/100#issuecomment-733033859), hence `d2b` was born.

## `d2b` and `dcm2bids`

Similarities:

- **Config files used with `dcm2bids` are compatible with `d2b`**
- The `d2b run` command corresponds to `dcm2bids`
- The `d2b scaffold` command corresponds to `dcm2bids_scaffold`

Differences:

- `d2b` has a plugin system so that users can extend the core functionality to fit the needs of their specific use-case.
- The `d2b` code architecture is meant to make the BIDS dataset generation process less error prone.
- Out of the box, `d2b` doesn't try to convert DICOM files and in fact `dcm2niix` doesn't even need to be installed. To do DICOM -> BIDS conversions install the [`d2b-dcm2niix`](https://github.com/d2b-dev/d2b-dcm2niix) plugin
- Out of the box `defaceTpl` is no longer supported.

<!-- ## Config File Schema -->

## The plugin system

`d2b` uses [`pluggy`](https://github.com/pytest-dev/pluggy) to faciliate the discorvery and integration of plugins, as such familiarity with the [pluggy documentation](https://pluggy.readthedocs.io/en/latest/) is helpful.

That said, here's a small example:

Let's write a plugin that adds the command `d2b hello <name>` to `d2b`.

The convention is to name the package implementing the plugin `d2b-[plugin-name]`, so we'll name our package `d2b-hello`.

Let's add the plugin implementation

`d2b-hello/d2b_hello.py`:

```python
from __future__ import annotations

import argparse

from d2b.hookspecs import hookimpl


@hookimpl
def register_commands(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser("hello")
    parser.add_argument("name", help="Greet this person")
    parser.add_argument("--shout", action="store_true", help="Shout it!")
    parser.set_defaults(handler=handler)


def handler(args: argparse.Namespace):
    name: str = args.name
    shout: bool | None = args.shout
    greeting = f"Hello, {name}!"
    print(greeting.upper() if shout else greeting)
```

The script above is tapping into one of the various pluggable locations (hookspecs in pluggy speak) by providing and implementation (hookimpl) of one of the desired hookspecs (`register_commands`) exposed by `d2b`.

There are many spots in `d2b` which allow for a user to extend or change the core functionality. Check out the module [`hookspecs.py`](https://github.com/d2b-dev/d2b/blob/master/src/d2b/hookspecs.py) to see which hooks are available.

In the case above `register_commands` is one of the hookspecs defined by `d2b` enabling for plugins to add subcommands to the `d2b` CLI.

How do we tell `d2b` about our plugin?

To discover the plugin `d2b` (via `pluggy`) uses [entrypoints](https://pluggy.readthedocs.io/en/latest/#loading-setuptools-entry-points). So we'll add a basic `setup.py` module:

`d2b-hello/setup.py`:

```python
from setuptools import find_packages
from setuptools import setup

setup(
    name="d2b-hello",
    install_requires="d2b>=0.2.3,<1.0",
    entry_points={"d2b": ["d2b-hello=d2b_hello"]},
    packages=find_packages(),
)
```

And now we can install our plugin:

```bash
pip install -e ./d2b-hello/
```

After which we have:

```bash
$ d2b --help
usage: d2b [-h] [-v] {run,scaffold,hello} ...

d2b - Organize data in the BIDS format

positional arguments:
  {run,scaffold,hello}

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
```

Our `d2b hello` subcommand is there!

```bash
$ d2b hello --help
usage: d2b hello [-h] [--shout] name

positional arguments:
  name        Greet this person

optional arguments:
  -h, --help  show this help message and exit
  --shout     Shout it!
```

And, trying it out:

```bash
$ d2b hello Andrew --shout
HELLO, ANDREW!
```

Success! 🏆
