from __future__ import annotations

import json
import os
from dataclasses import dataclass
from dataclasses import field
from io import StringIO
from pathlib import Path
from typing import Any
from typing import TextIO


@dataclass
class DatasetDescription:
    name: str = ""
    bids_version: str = ""
    dataset_type: str = "raw"
    license: str = ""
    authors: list[str] = field(default_factory=lambda: [""])
    acknowledgements: str = ""
    how_to_acknowledge: str = ""
    funding: list[str] = field(default_factory=lambda: [""])
    ethics_approvals: list[str] = field(default_factory=lambda: [""])
    references_and_links: list[str] = field(default_factory=lambda: [""])
    dataset_doi: str = ""
    hed_version: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]):
        return cls(
            name=d.get("Name", ""),
            bids_version=d.get("BIDSVersion", ""),
            dataset_type=d.get("DatasetType", ""),
            license=d.get("License", ""),
            authors=d.get("Authors") or [""],
            acknowledgements=d.get("Acknowledgements", ""),
            how_to_acknowledge=d.get("HowToAcknowledge", ""),
            funding=d.get("Funding") or [""],
            ethics_approvals=d.get("EthicsApprovals") or [""],
            references_and_links=d.get("ReferencesAndLinks") or [""],
            dataset_doi=d.get("DatasetDOI", ""),
            hed_version=d.get("HEDVersion", ""),
        )

    @classmethod
    def from_file(cls, f: TextIO):
        return cls.from_dict(json.load(f))

    @classmethod
    def from_filename(cls, filename: str | Path):
        with open(filename) as f:
            return cls.from_file(f)

    def to_dict(self):
        return {
            "Name": self.name,
            "BIDSVersion": self.bids_version,
            "DatasetType": self.dataset_type,
            "License": self.license,
            "Authors": self.authors,
            "Acknowledgements": self.acknowledgements,
            "HowToAcknowledge": self.how_to_acknowledge,
            "Funding": self.funding,
            "EthicsApprovals": self.ethics_approvals,
            "ReferencesAndLinks": self.references_and_links,
            "DatasetDOI": self.dataset_doi,
            "HEDVersion": self.hed_version,
        }

    def to_file(self, f: TextIO | None = None) -> TextIO:
        _f = f or StringIO()
        json.dump(self.to_dict(), _f, indent=2)
        _f.write(os.linesep)
        _f.seek(0)
        return _f

    def to_filename(self, filename: str | Path) -> Path:
        path = Path(filename)
        path.write_text(self.to_file().read())
        return path
