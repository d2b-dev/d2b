from __future__ import annotations

import itertools
import logging
import os
import platform
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import DefaultDict
from typing import Iterator
from typing import TypeVar

from d2b import defaults
from d2b.plugins import pm
from d2b.utils import associated_nii_ext
from d2b.utils import prepend
from d2b.utils import rsync
from d2b.utils import splitext

__version__ = "1.1.5"


T = TypeVar("T")


class D2B:
    def __init__(
        self,
        in_dirs: str | Path | list[str | Path],
        out_dir: str | Path,
        config_file: Path,
        participant: str,
        session: str = defaults.session,
        options: dict[str, Any] = None,  # from the cli
    ):
        self.config: dict[str, Any]  # set by calling self.load_config()
        self.files: list[Path]  # set in self.run()
        self.descriptions: list[Description]  # set in self.run()
        self.matcher: Matcher  # set in self.run()

        self.in_dirs = (
            [Path(d) for d in in_dirs] if isinstance(in_dirs, list) else [Path(in_dirs)]
        )
        self.out_dir = Path(out_dir)
        self.config_file = Path(config_file)
        self.participant = Participant(participant, session)
        self.options = options or {}

        self.d2b_dir = self.out_dir / defaults.d2b_dir_name

        self._configure_logger()  # logging setup

    @property
    def in_dirs(self) -> list[Path]:
        return self._in_dirs

    @in_dirs.setter
    def in_dirs(self, value: list[Path]):
        dir_not_found = [d for d in value if not d.is_dir()]
        if dir_not_found:
            raise FileNotFoundError(dir_not_found)
        self._in_dirs = value

    def load_config(self):
        self.config = pm.hook.load_config(  # type: ignore
            path=self.config_file,
            d2b=self,
        )

    def pre_run_logs(self):
        self.logger.info("--- d2b start ---")
        self.logger.info("OS:version: %s", platform.platform())
        self.logger.info("python:version: %s", sys.version.replace("\n", ""))
        self.logger.info("d2b:version: %s", __version__)
        self.logger.info("participant: %s", self.participant.bids_label)
        self.logger.info("session: %s", self.participant.bids_session)
        self.logger.info("config: %s", os.path.realpath(self.config_file))
        self.logger.info("BIDS directory: %s", os.path.realpath(self.out_dir))

        pm.hook.pre_run_logs(logger=self.logger, d2b=self)  # type: ignore

    def run(self):
        self.pre_run_logs()

        # make copies of the input directories
        dst_parent = self.d2b_dir / "src"
        for i, in_dir in enumerate(self.in_dirs):
            dst_dir = dst_parent / f"{self.participant.directory}" / f"folder{i:02}"
            dst_dir.mkdir(exist_ok=True, parents=True)
            msg = f"Copying folder [{in_dir}] to temporary location [{dst_dir}]"
            self.logger.info(msg)
            rsync(in_dir, dst_dir)

        # collect files for description-matching
        self.logger.info("Collecting files")
        collected_files: list[list[Path]] = pm.hook.collect_files(  # type: ignore
            out_dir=self.out_dir,
            d2b_dir=self.d2b_dir,
            config=self.config,
            options=self.options,
            d2b=self,
        )
        # each hook returns a list of files
        self.files = sorted(set(itertools.chain(*collected_files)))

        # load the descriptions
        self.descriptions = [
            Description.from_dict(i, d)
            for i, d in enumerate(self.config["descriptions"])
        ]
        self.check_descriptions(self.descriptions)

        # run the matching algorithm
        self.matcher = Matcher(
            self.participant,
            self.descriptions,
            self.files,
            self.config,
            self.options,
        )
        self.matcher.run()

        # run pre-move hooks
        self.logger.info("Running pre-move hooks")
        pm.hook.pre_move(  # type: ignore
            acquisitions=self.matcher.acquisitions,
            config=self.config,
            options=self.options,
            d2b=self,
        )

        # move the files
        self.logger.info("Moving acquisitions into BIDS folder")
        for acquisition in self.matcher.acquisitions:
            pm.hook.move(  # type: ignore
                out_dir=self.out_dir,
                acquisition=acquisition,
                acquisitions=self.matcher.acquisitions,
                config=self.config,
                options=self.options,
                d2b=self,
            )

        # run post-move hooks
        self.logger.info("Running post-move hooks")
        pm.hook.post_move(  # type: ignore
            out_dir=self.out_dir,
            acquisitions=self.matcher.acquisitions,
            config=self.config,
            options=self.options,
            d2b=self,
        )

    def check_descriptions(self, descriptions: list[Description]):
        agg: dict[Description, list[Description]] = defaultdict(list)
        for d in descriptions:
            agg[d].append(d)

        for ds in agg.values():
            if len(ds) <= 1:
                continue
            idxs = [d.index for d in ds]
            dtype = ds[0].data_type
            mlabel = ds[0].modality_label
            clabels = ds[0].custom_labels
            self.logger.warning(
                f"❗ Descriptions at positions {idxs} have matching dataType [{dtype}], "
                f"modalityLabel [{mlabel}], and customLabels [{clabels}]. "
                "Files which match with these distinct descriptions will be "
                "considered two different runs of the same type of acquisition. "
                "If this is intentional, please ignore this warning.",
            )

    def _configure_logger(self):
        _prefix = self.participant.prefix
        _now = datetime.now().isoformat().replace(":", "")

        log_level = self.options.get("log_level", "INFO")
        log_file = self.d2b_dir / "log" / f"{_prefix}_{_now}.log"
        log_file.parent.mkdir(exist_ok=True, parents=True)

        _setup_logging(log_level, log_file)

        self.logger = logging.getLogger(__name__)


class Matcher:
    def __init__(
        self,
        participant: Participant,
        descriptions: list[Description],
        files: list[Path],
        config: dict[str, Any] = None,  # d2b config
        options: dict[str, Any] = None,  # from the cli
    ):
        self.participant = participant
        self.descriptions = descriptions
        self.files = files
        self.config = config or {}
        self.options = options or {}

        self.logger = logging.getLogger(__name__)

        # populated in self.find_matches()
        self.file_to_acq: dict[Path, list[Acquisition]] = {fp: [] for fp in files}
        # populated in self.remove_multimatch()
        self.acquisitions: list[Acquisition] = []

    def run(self):
        self.find_matches()
        self.filter_unique_matches()
        self.dedup_runs()
        self.resolve_matches_intended_for()

    def find_matches(self):
        possible_matches = itertools.product(self.files, self.descriptions)
        for fp, description in possible_matches:
            criteria = description.data.get("criteria")
            possible_link = pm.hook.is_link(  # type: ignore
                path=fp,
                criteria=criteria,
                config=self.config,
                options=self.options,
            )
            if criteria is None or not any(possible_link):
                continue
            acquisition = Acquisition(fp, self.participant, description.copy())
            self.file_to_acq[fp].append(acquisition)

    def filter_unique_matches(self):
        """Keep only the matches (acquisitions/files) which match a single
        description. Do some logging along the way.
        """
        for fp, acquisitions in self.file_to_acq.items():
            if len(acquisitions) == 0:
                self.logger.info(f"➖ File [{fp}] matched [0] descriptions")
            elif len(acquisitions) > 1:
                N = len(acquisitions)
                idxs = [acq.description.index for acq in acquisitions]
                msg = (
                    f"❗ File [{fp}] matched [{N}] descriptions. Skipping. "
                    f"Matching descriptions {idxs}"
                )
                self.logger.warning(msg)
                for acq in acquisitions:
                    idx = acq.description.index
                    dtype = acq.description.data_type
                    mlabel = acq.description.modality_label
                    msg = f"description [{idx}] dataType [{dtype}] modality [{mlabel}]"
                    self.logger.warning(" " * 4 + msg)
            else:
                # yay this acquisition matched exactly one description!
                idx = acquisitions[0].description.index
                msg = (
                    f"✅ File [{fp}] matched [1] description. "
                    f"Matching description [{idx}]"
                )
                self.logger.info(msg)
                self.acquisitions.append(acquisitions[0])

    def dedup_runs(self):
        """
        Check if there is duplicate destination roots among the acquisitions
        and add '_run-' to the customLabels of any such acquisition
        """
        # NOTE: what happens if two acquisitions are deemed to be "duplicates"
        # here (i.e. they have the same dst_root) but aren't actually different
        # runs? Under this paradigm/implementation two acquisitions are duplicates
        # iff two _distinct_ files each have a corresponding description which are
        # "equivalent" (i.e same dataType, modalityLabel, and customLabels), in
        # which case this indicates that the descriptions themselves are not
        # granular enough to unabiguously distinguish between these
        # fundamentally distinct files/acquisitions.
        dst_roots = [acq.dst_root for acq in self.acquisitions]
        for dst_root, dupe_locations in self._duplicates(dst_roots):
            self.logger.info(f"[{dst_root}] has [{len(dupe_locations)}] runs")
            self.logger.info("Adding 'run' information to the acquisition")
            for run_num, acq_idx in enumerate(dupe_locations, 1):
                run_str = defaults.run_tpl.format(run_num)
                acq = self.acquisitions[acq_idx]
                acq.description.custom_labels += run_str

    def _duplicates(self, seq: list[T]) -> Iterator[tuple[T, list[int]]]:
        """Find duplicate items in a list (http://stackoverflow.com/a/5419576)"""
        position_map: DefaultDict[T, list[int]] = defaultdict(list)
        for position, item in enumerate(seq):
            position_map[item].append(position)

        for key, positions in position_map.items():
            if len(positions) > 1:
                yield key, positions

    def resolve_matches_intended_for(self):
        for acq in self.acquisitions:
            description = acq.description
            intended_for = description.intended_for

            if intended_for is None:
                continue

            elif isinstance(intended_for, int) or isinstance(intended_for, str):
                fp = self._resolve_intended_for_path(acq, intended_for)
                if fp is None:
                    continue
                acq.data["IntendedFor"] = str(fp)

            elif isinstance(intended_for, list):
                for _intended_for in intended_for:
                    fp = self._resolve_intended_for_path(acq, _intended_for)
                    if fp is None:
                        continue
                    if acq.data.get("IntendedFor") is None:
                        acq.data["IntendedFor"] = []
                    acq.data["IntendedFor"].append(str(fp))

            else:
                raise ValueError(
                    f"Invalid IntendedFor value [{intended_for}] in "
                    f"description at index [{description.index}]",
                )

    def _resolve_intended_for_path(
        self,
        acq: Acquisition,
        intended_for: int | str,
    ) -> Path | None:
        target_acq = self._resolve_intended_for(self.acquisitions, intended_for)
        if target_acq is None:
            return
        ext = associated_nii_ext(target_acq.src_file)
        if ext is None:
            self._log_associated_nii_not_found(acq, target_acq)
            return
        bids_path = target_acq.dst_root.with_suffix(ext)
        return bids_path.relative_to(target_acq.participant.subject_directory)

    @staticmethod
    def _resolve_intended_for(
        acquisitions: list[Acquisition],
        intended_for: int | str,
    ) -> Acquisition | None:
        if isinstance(intended_for, int):
            match_refs = [
                a for a in acquisitions if a.description.index == intended_for
            ]
        elif isinstance(intended_for, str):
            match_refs = [
                a for a in acquisitions if a.description.data.get("id") == intended_for
            ]
        else:
            msg = (
                "IntendedFor field must be of type int | str | (int | str)[]. "
                f"Found [{intended_for!r}]"
            )
            raise ValueError(msg)

        if len(match_refs) == 0:
            # this case can happen if IntendedFor references a
            # description for which there was no match. In this
            # case we just return nothing (and in turn should
            # skip adding this IntendedFor to the sidecar's data.
            return

        return match_refs[0]

    def _log_associated_nii_not_found(self, acq: Acquisition, target_acq: Acquisition):
        msg = (
            f"No NIfTI file associated with file [{target_acq.src_file}]. "
            "This acquisition was determined to be one of the IntendedFor "
            f"acquisitions for the file [{acq.src_file}] matching description "
            f"at index [{acq.description.index}]"
        )
        self.logger.warning(msg)


class Acquisition:
    """By definition (we declare here) an `Acquisition` is a set of files
    which share a file stem, where stem (essentially) means the path,
    without the extension/suffix, relative to the bids/output direcotry.

    In effect, any file which has been deemed, through whatever means,
    to match a given `Description`, then that file together with the
    afore-mentioned description is enough to constitue an `Acquisition`.

    So in this sense an Acquisition need not, necessarily, be an "image",
    although this is usually the case.
    """

    def __init__(
        self,
        src_file: str | Path,
        participant: Participant,
        description: Description,
        data: dict[str, Any] = None,
    ):
        self.src_file = Path(src_file)
        self.participant = participant
        self.description = description
        self.data = data or {}

    def __eq__(self, o):
        return (
            self.participant.prefix == o.participant.prefix
            and self.description.data_type == o.description.data_type
            and self.description.suffix == o.description.suffix
        )

    @property
    def src_root(self) -> Path:
        return splitext(self.src_file)[0]

    @property
    def dst_root_no_modality(self) -> Path:
        dtype_dir = self.participant.directory / self.description.data_type
        return (
            dtype_dir
            / f"{self.participant.prefix}{self.description.suffix_no_modality}"
        )

    @property
    def dst_root(self) -> Path:
        dtype_dir = self.participant.directory / self.description.data_type
        return dtype_dir / f"{self.participant.prefix}{self.description.suffix}"


class Participant:
    def __init__(self, label: str, session: str = ""):
        self._label: str
        self._session: str

        self.label = label
        self.session = session

    def __repr__(self):
        return f"{self.__class__.__name__}({self.label!r}, {self.session!r})"

    # getters/setters
    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, lab: str):
        _l = lab.strip().replace("sub-", "")
        if not _l.isalnum():
            raise ValueError(
                f"Participant label for must be alpha-numeric. Found: {_l}",
            )
        self._label = _l.strip()

    @property
    def session(self):
        return self._session

    @session.setter
    def session(self, ses: str):
        _s = ses.strip().replace("ses-", "")
        if not _s.isalnum() and _s != "":
            raise ValueError(
                f"Participant session ID must be alpha-numeric. Found: {_s}",
            )
        self._session = _s.strip()

    # computed properties
    @property
    def bids_label(self):
        return f"sub-{self.label}"

    @property
    def bids_session(self):
        return f"ses-{self._session}" if self.session else ""

    @property
    def prefix(self):
        lab, ses = self.bids_label, self.bids_session
        return f"{lab}_{ses}" if ses else lab

    @property
    def directory(self):
        lab, ses = self.bids_label, self.bids_session
        return Path(lab, ses) if ses else Path(lab)

    @property
    def subject_directory(self):
        return Path(self.bids_label)


class Description:
    DATATYPES = ["anat", "beh", "dwi", "eeg", "fmap", "func", "ieeg", "meg", "perf"]

    def __init__(
        self,
        index: int,
        data_type: str,
        modality_label: str,
        custom_labels: str | dict[str, str] = "",
        sidecar_changes: dict[str, Any] | None = None,
        intended_for: int | str | list[int | str] | None = None,
        data: dict[str, Any] = None,
    ):
        self.index = index
        self.data_type = data_type
        self.modality_label = modality_label

        self.custom_labels = custom_labels or ""
        self.sidecar_changes = sidecar_changes or {}
        self.intended_for = intended_for
        self.data = data or {}

    def __eq__(self, o):
        return hash(self) == hash(o)

    def __hash__(self):
        return hash((self.data_type, self.modality_label, self.custom_labels))

    @classmethod
    def from_dict(cls, index: int, data: dict[str, Any]):
        return cls(
            index=index,
            data_type=data["dataType"],
            modality_label=data["modalityLabel"],
            custom_labels=data.get("customLabels", ""),
            sidecar_changes=data.get("sidecarChanges"),
            intended_for=data.get("IntendedFor"),
            data=data,
        )

    def copy(self):
        return self.__class__(
            index=self.index,
            data_type=self.data_type,
            modality_label=self.modality_label,
            custom_labels=self.custom_labels,
            sidecar_changes=self.sidecar_changes,
            intended_for=self.intended_for,
            data=self.data,
        )

    # getter/setters
    @property
    def data_type(self) -> str:
        return self._data_type

    @data_type.setter
    def data_type(self, val: str):
        if val not in self.DATATYPES:
            msg = f"Description dataType must be one of {self.DATATYPES}. Found [{val}]"
            raise ValueError(msg)
        self._data_type = val

    @property
    def modality_label(self) -> str:
        return self._modality_label

    @modality_label.setter
    def modality_label(self, val: str):
        self._modality_label = prepend(val, "_")

    @property
    def custom_labels(self):
        return prepend(str(self._custom_labels), "_")

    @custom_labels.setter
    def custom_labels(self, val: str | dict[str, str]):
        if isinstance(val, str):
            self._custom_labels = FilenameEntities.from_string(val)
        else:
            self._custom_labels = FilenameEntities(val)

    # computed properties
    @property
    def suffix_no_modality(self) -> str:
        return self.custom_labels

    @property
    def suffix(self) -> str:
        return f"{self.custom_labels}{self.modality_label}"


class FilenameEntities:
    # the order matters (BIDS v1.6 - https://bids-specification.readthedocs.io/en/v1.6.0/99-appendices/09-entities.html#trc) # noqa: E501
    KNOWN_ENTITIES = (
        "sub",
        "ses",
        "task",
        "acq",
        "ce",
        "trc",
        "rec",
        "dir",
        "run",
        "mod",
        "echo",
        "flip",
        "inv",
        "mt",
        "part",
        "recording",
        "proc",
        "space",
        "split",
        "res",
        "den",
        "label",
        "desc",
    )

    def __init__(self, entities: dict[str, str]):
        self.entities = self.parse(entities)

    def __repr__(self):
        return f"{self.__class__.__name__}({dict(self)!r})"

    def __str__(self):
        return "_".join(f"{k}-{v}" for k, v in self)

    def __iter__(self) -> Iterator[tuple[str, str]]:
        _d = self.entities.copy()

        for k in self.KNOWN_ENTITIES:
            v = _d.pop(k, None)
            if v is None:
                continue
            yield (k, v)

        for k, v in _d.items():
            yield (k, v)

    @classmethod
    def from_string(cls, s: str):
        return cls(cls.parse(s))

    @classmethod
    def parse(cls, entities: str | dict[str, str]) -> dict[str, str]:
        if isinstance(entities, dict):
            return entities
        stripped_entities = entities.strip().strip("_")
        if stripped_entities == "":
            return {}
        entity_strs = entities.strip().strip("_").split("_")
        return dict(map(cls._split_entity_str, entity_strs))

    @staticmethod
    def _split_entity_str(s: str) -> tuple[str, str]:
        parts = s.strip().split("-")
        if len(parts) < 2:
            m = (
                f"Failed parsing entity string [{s!r}]. "
                "String must have at least one hyphen."
            )
            raise ValueError(m)
        k = parts[0]
        v = "".join(filter(str.isalnum, "".join(parts[1:])))
        return k, v


def _setup_logging(log_level, logFile=None):
    """Setup logging configuration"""
    logging.basicConfig()
    logger = logging.getLogger()

    # Check level
    level = getattr(logging, log_level.upper(), None)
    if not isinstance(level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    logger.setLevel(level)

    # Set FileHandler
    if logFile:
        formatter = logging.Formatter(logging.BASIC_FORMAT)
        handler = logging.FileHandler(logFile)
        handler.setFormatter(formatter)
        handler.setLevel("DEBUG")
        logger.addHandler(handler)
