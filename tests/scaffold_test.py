import filecmp
from pathlib import Path

from d2b.scaffold import DatasetDescription


class TestDatasetDescription:
    def test_init_defaults(self):
        d = DatasetDescription()

        assert d.name == ""
        assert d.bids_version == ""
        assert d.dataset_type == "raw"
        assert d.license == ""
        assert d.authors == [""]
        assert d.acknowledgements == ""
        assert d.how_to_acknowledge == ""
        assert d.funding == [""]
        assert d.ethics_approvals == [""]
        assert d.references_and_links == [""]
        assert d.dataset_doi == ""
        assert d.hed_version == ""

    def test_init(self):
        d = DatasetDescription(
            "a",
            "b",
            "derived",
            "c",
            ["d"],
            "e",
            "f",
            ["g"],
            ["h"],
            ["i"],
            "k",
            "l",
        )

        assert d.name == "a"
        assert d.bids_version == "b"
        assert d.dataset_type == "derived"
        assert d.license == "c"
        assert d.authors == ["d"]
        assert d.acknowledgements == "e"
        assert d.how_to_acknowledge == "f"
        assert d.funding == ["g"]
        assert d.ethics_approvals == ["h"]
        assert d.references_and_links == ["i"]
        assert d.dataset_doi == "k"
        assert d.hed_version == "l"

    def test_from_dict(self):
        d = DatasetDescription.from_dict({})

        assert d.name == ""
        assert d.bids_version == ""
        assert d.dataset_type == "raw"
        assert d.license == ""
        assert d.authors == [""]
        assert d.acknowledgements == ""
        assert d.how_to_acknowledge == ""
        assert d.funding == [""]
        assert d.ethics_approvals == [""]
        assert d.references_and_links == [""]
        assert d.dataset_doi == ""
        assert d.hed_version == ""

    def test_from_dict_non_empty(self):
        data = {
            "Name": "a",
            "BIDSVersion": "b",
            "DatasetType": "derived",
            "License": "c",
            "Authors": ["d"],
            "Acknowledgements": "e",
            "HowToAcknowledge": "f",
            "Funding": ["g"],
            "EthicsApprovals": ["h"],
            "ReferencesAndLinks": ["i"],
            "DatasetDOI": "k",
            "HEDVersion": "l",
        }
        d = DatasetDescription.from_dict(data)

        assert d.name == "a"
        assert d.bids_version == "b"
        assert d.dataset_type == "derived"
        assert d.license == "c"
        assert d.authors == ["d"]
        assert d.acknowledgements == "e"
        assert d.how_to_acknowledge == "f"
        assert d.funding == ["g"]
        assert d.ethics_approvals == ["h"]
        assert d.references_and_links == ["i"]
        assert d.dataset_doi == "k"
        assert d.hed_version == "l"

    def test_to_dict(self):
        d = DatasetDescription(
            "a",
            "b",
            "derived",
            "c",
            ["d"],
            "e",
            "f",
            ["g"],
            ["h"],
            ["i"],
            "k",
            "l",
        )
        data = d.to_dict()

        assert data["Name"] == "a"
        assert data["BIDSVersion"] == "b"
        assert data["DatasetType"] == "derived"
        assert data["License"] == "c"
        assert data["Authors"] == ["d"]
        assert data["Acknowledgements"] == "e"
        assert data["HowToAcknowledge"] == "f"
        assert data["Funding"] == ["g"]
        assert data["EthicsApprovals"] == ["h"]
        assert data["ReferencesAndLinks"] == ["i"]
        assert data["DatasetDOI"] == "k"
        assert data["HEDVersion"] == "l"

    def test_from_file(self, scaffold_test_data: Path):
        with open(scaffold_test_data / "dataset_description.json") as f:
            d = DatasetDescription.from_file(f)

        assert d.name == "a"
        assert d.bids_version == "b"
        assert d.dataset_type == "derived"
        assert d.license == "c"
        assert d.authors == ["d"]
        assert d.acknowledgements == "e"
        assert d.how_to_acknowledge == "f"
        assert d.funding == ["g"]
        assert d.ethics_approvals == ["h"]
        assert d.references_and_links == ["i"]
        assert d.dataset_doi == "k"
        assert d.hed_version == "l"

    def test_from_filename(self, scaffold_test_data: Path):
        in_file = scaffold_test_data / "dataset_description.json"
        d = DatasetDescription.from_filename(in_file)

        assert d.name == "a"
        assert d.bids_version == "b"
        assert d.dataset_type == "derived"
        assert d.license == "c"
        assert d.authors == ["d"]
        assert d.acknowledgements == "e"
        assert d.how_to_acknowledge == "f"
        assert d.funding == ["g"]
        assert d.ethics_approvals == ["h"]
        assert d.references_and_links == ["i"]
        assert d.dataset_doi == "k"
        assert d.hed_version == "l"

    def test_to_file(self, tmpdir: str, scaffold_test_data: Path):
        d = DatasetDescription(
            "a",
            "b",
            "derived",
            "c",
            ["d"],
            "e",
            "f",
            ["g"],
            ["h"],
            ["i"],
            "k",
            "l",
        )

        out_file = Path(tmpdir) / "dataset_description.json"
        with open(out_file, "w") as f:
            d.to_file(f)

        expected = scaffold_test_data / "dataset_description.json"
        assert filecmp.cmp(out_file, expected)

    def test_to_filename(self, tmpdir: str, scaffold_test_data: Path):
        d = DatasetDescription(
            "a",
            "b",
            "derived",
            "c",
            ["d"],
            "e",
            "f",
            ["g"],
            ["h"],
            ["i"],
            "k",
            "l",
        )

        out_file = Path(tmpdir) / "dataset_description.json"
        d.to_filename(out_file)

        expected = scaffold_test_data / "dataset_description.json"
        assert filecmp.cmp(out_file, expected)
