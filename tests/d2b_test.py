from __future__ import annotations

import filecmp
import json
import logging
from pathlib import Path

import pytest
from d2b.d2b import __version__
from d2b.d2b import Acquisition
from d2b.d2b import D2B
from d2b.d2b import Description
from d2b.d2b import FilenameEntities
from d2b.d2b import IntendedForResolver
from d2b.d2b import Matcher
from d2b.d2b import Participant
from pytest import LogCaptureFixture
from pytest_mock import MockerFixture


class TestFilenameEntities:
    def test_init(self):
        entities = {"acq": "2", "sub": "1"}  # note the wrong order
        fe = FilenameEntities(entities)
        assert fe.entities == entities
        assert str(fe) == "sub-1_acq-2"
        assert list(fe) == [("sub", "1"), ("acq", "2")]
        assert repr(fe) == "FilenameEntities({'sub': '1', 'acq': '2'})"

    def test_init_with_illegal_entity_values(self):
        fe = FilenameEntities({"acq": "a-b.c", "sub": "abc?1"})  # note the wrong order
        assert fe.entities == {"acq": "abc", "sub": "abc1"}
        assert str(fe) == "sub-abc1_acq-abc"
        assert list(fe) == [("sub", "abc1"), ("acq", "abc")]

    def test_init_with_empty_entities(self):
        entities = {}
        fe = FilenameEntities(entities)
        assert fe.entities == entities
        assert str(fe) == ""
        assert list(fe) == []

    def test_from_string(self):
        entities = "_acq-2_unknown-def_sub-abc123"  # note the wrong order
        fe = FilenameEntities.from_string(entities)
        assert fe.entities == {"acq": "2", "sub": "abc123", "unknown": "def"}
        assert str(fe) == "sub-abc123_acq-2_unknown-def"
        assert list(fe) == [("sub", "abc123"), ("acq", "2"), ("unknown", "def")]

    def test_from_string_with_illegal_entity_values(self):
        s = "_acq-a-b.c_sub-abc?1_"  # note the wrong order
        fe = FilenameEntities.from_string(s)
        assert fe.entities == {"acq": "abc", "sub": "abc1"}
        assert str(fe) == "sub-abc1_acq-abc"
        assert list(fe) == [("sub", "abc1"), ("acq", "abc")]

    def test_from_string_empty_string(self):
        entities = ""
        fe = FilenameEntities.from_string(entities)
        assert fe.entities == {}
        assert str(fe) == ""
        assert list(fe) == []

    def test_from_string_raises_when_given_badly_formatted_entities(self):
        entities = "acq"
        with pytest.raises(ValueError):
            FilenameEntities.from_string(entities)


class TestDescription:
    @pytest.mark.parametrize(("mlabel", "expected_mlabel"), [("", ""), ("a", "_a")])
    def test_init(self, mlabel, expected_mlabel):
        description = Description(0, "func", mlabel, "dir-AP", {"a": 1}, 0, {"b": 2})
        assert description.index == 0
        assert description.data_type == "func"
        assert description.modality_label == expected_mlabel
        assert description.custom_labels == "_dir-AP"
        assert description.sidecar_changes == {"a": 1}
        assert description.intended_for == 0
        assert description.data == {"b": 2}

    @pytest.mark.parametrize(("mlabel", "expected_mlabel"), [("", ""), ("a", "_a")])
    def test_init_defaults(self, mlabel, expected_mlabel):
        description = Description(0, "func", mlabel)
        assert description.index == 0
        assert description.data_type == "func"
        assert description.modality_label == expected_mlabel
        assert description.custom_labels == ""
        assert description.sidecar_changes == {}
        assert description.intended_for is None
        assert description.data == {}

    def test_init_raises_with_invalid_data_type(self):
        with pytest.raises(ValueError):
            Description(0, "", "")

    @pytest.mark.parametrize(
        "dtype",
        ["anat", "beh", "dwi", "eeg", "fmap", "func", "ieeg", "meg", "perf"],
    )
    def test_valid_data_types(self, dtype):
        assert Description(0, dtype, "")

    @pytest.mark.parametrize(
        "clabels",
        ["dir-def_acq-abc_", {"dir": "def", "acq": "abc"}],
        ids=["from_string", "from_dict"],
    )
    def test_custom_labels(self, clabels):
        desc = Description(0, "func", "", custom_labels=clabels)
        assert desc.custom_labels == "_acq-abc_dir-def"

    @pytest.mark.parametrize(
        ("mlabel", "clabels", "expected"),
        [
            ("", "", ""),
            ("asl", "", "_asl"),
            ("_asl", "", "_asl"),
            ("", "dir-AP_acq-abc", "_acq-abc_dir-AP"),
            ("", "_dir-AP_acq-abc", "_acq-abc_dir-AP"),
            ("asl", "dir-AP_acq-abc", "_acq-abc_dir-AP_asl"),
            ("_asl", "_dir-AP_acq-abc", "_acq-abc_dir-AP_asl"),
            ("", {"dir": "AP", "acq": "abc"}, "_acq-abc_dir-AP"),
            ("", {"dir": "AP", "acq": "abc"}, "_acq-abc_dir-AP"),
            ("asl", {"dir": "AP", "acq": "abc"}, "_acq-abc_dir-AP_asl"),
            ("_asl", {"dir": "AP", "acq": "abc"}, "_acq-abc_dir-AP_asl"),
        ],
    )
    def test_suffix_methods(self, mlabel, clabels, expected):
        desc = Description(0, "func", mlabel, custom_labels=clabels)
        assert desc.suffix == expected
        assert desc.suffix_no_modality == desc.custom_labels

    @pytest.mark.parametrize(
        ("index", "data", "expected_description"),
        [
            (
                1,
                {"dataType": "func", "modalityLabel": "mlab"},
                Description(1, "func", "mlab"),
            ),
            (
                2,
                {
                    "dataType": "func",
                    "modalityLabel": "mlab",
                    "customLabels": "run-1",
                    "sidecarChanges": {"a": 1},
                    "IntendedFor": 0,
                },
                Description(2, "func", "mlab", "run-1", {"a": 1}, 0),
            ),
            (
                3,
                {
                    "dataType": "func",
                    "modalityLabel": "mlab",
                    "extra_key": "extra_value",
                },
                Description(3, "func", "mlab", data={"extra_key": "extra_value"}),
            ),
            (
                4,
                {
                    "dataType": "func",
                    "modalityLabel": "mlab",
                    "customLabels": "run-1",
                    "sidecarChanges": {"a": 1},
                    "IntendedFor": 0,
                    "extra_key": "extra_value",
                },
                Description(
                    4,
                    "func",
                    "mlab",
                    "run-1",
                    {"a": 1},
                    0,
                    {"extra_key": "extra_value"},
                ),
            ),
        ],
        ids=[
            "minimum_keys",
            "all_expected_keys",
            "minimum_keys_with_extra_unknown_keys",
            "all_expected_keys_with_extra_unknown_keys",
        ],
    )
    def test_from_dict(self, index, data, expected_description):
        description = Description.from_dict(index, data)
        # testing __eq__
        assert description == expected_description
        # testing that all attributes are as expected
        assert description.index == expected_description.index
        assert description.data_type == expected_description.data_type
        assert description.modality_label == expected_description.modality_label
        assert description.custom_labels == expected_description.custom_labels
        assert description.sidecar_changes == expected_description.sidecar_changes
        assert description.intended_for == expected_description.intended_for
        assert description.data == expected_description.data

    def test_copy(self):
        d1 = Description(4, "func", "mlab", "run-1", {"a": 1}, [0], {"b": "2"})
        d2 = d1.copy()

        assert d1 == d2
        # testing that all attributes are equal
        assert d1.index == d2.index
        assert d1.data_type == d2.data_type
        assert d1.modality_label == d2.modality_label
        assert d1.custom_labels == d2.custom_labels
        assert d1.sidecar_changes == d2.sidecar_changes
        assert d1.intended_for == d2.intended_for
        assert d1.data == d2.data
        # testing not the same object
        assert id(d1) != id(d2)
        # testing mutable attrs are not the same object
        d1.sidecar_changes["a"] = 11
        d1.intended_for.append(1)  # type: ignore
        d1.data["b"] = 22
        assert d1.sidecar_changes != d2.sidecar_changes
        assert d1.intended_for != d2.intended_for
        assert d1.data != d2.data

    def test_is_hashable(self):
        assert hash(Description(0, "func", ""))


class TestParticipant:
    def test_init_with_one_argument(self):
        participant = Participant("label01")
        assert participant.label == "label01"
        assert participant.bids_label == "sub-label01"
        assert participant.session == ""
        assert participant.bids_session == ""
        assert participant.prefix == "sub-label01"
        assert participant.directory == Path("sub-label01")
        assert participant.subject_directory == Path("sub-label01")

    def test_init_with_explicit_empty_session(self):
        participant = Participant("label01", "")
        assert participant.label == "label01"
        assert participant.bids_label == "sub-label01"
        assert participant.session == ""
        assert participant.bids_session == ""
        assert participant.prefix == "sub-label01"
        assert participant.directory == Path("sub-label01")
        assert participant.subject_directory == Path("sub-label01")

    def test_init_with_label_and_session(self):
        participant = Participant("label01", "session01")
        assert participant.label == "label01"
        assert participant.bids_label == "sub-label01"
        assert participant.session == "session01"
        assert participant.bids_session == "ses-session01"
        assert participant.prefix == "sub-label01_ses-session01"
        assert participant.directory == Path("sub-label01", "ses-session01")
        assert participant.subject_directory == Path("sub-label01")

    def test_init_with_label_and_session_that_already_have_prefixes_is_ok(self):
        participant = Participant("sub-label01", "ses-session01")
        assert participant.label == "label01"
        assert participant.bids_label == "sub-label01"
        assert participant.session == "session01"
        assert participant.bids_session == "ses-session01"
        assert participant.prefix == "sub-label01_ses-session01"
        assert participant.directory == Path("sub-label01", "ses-session01")
        assert participant.subject_directory == Path("sub-label01")

    def test_label_and_session_are_stripped_of_whitespace(self):
        participant = Participant(" label01 ", " session01 ")
        assert participant.label == "label01"
        assert participant.bids_label == "sub-label01"
        assert participant.session == "session01"
        assert participant.bids_session == "ses-session01"

    def test_raises_ValueError_if_label_is_empty(self):
        with pytest.raises(ValueError):
            Participant("")

    def test_raises_ValueError_if_label_is_not_alphanumeric(self):
        with pytest.raises(ValueError):
            Participant("label_01")

    def test_raises_ValueError_if_session_is_not_alphanumeric(self):
        with pytest.raises(ValueError):
            Participant("label", "session-01")

    def test_repr(self):
        participant = Participant("label01", "session01")
        assert str(participant) == "Participant('label01', 'session01')"

    def test_repr_empty_session(self):
        participant = Participant("label01")
        assert str(participant) == "Participant('label01', '')"

    def test_equality(self):
        p1 = Participant("a", "1")
        p2 = Participant("a", "1")
        p3 = Participant("b")

        assert p1 == p2
        assert p1 != p3

    def test_is_hashable(self):
        assert hash(Participant("a"))


class TestAcquisition:
    def test_init(self):
        src_file = Path("a.json")
        p = Participant("sub-01")
        d = Description(0, "func", "bold")
        data = {"a": 1}

        acq = Acquisition(src_file, p, d, data)

        assert acq.src_file == src_file
        assert acq.participant == p
        assert acq.description == d
        assert acq.data == data

    def test_init_defaults(self):
        src_file = Path("a.json")
        p = Participant("sub-01", "ses-01")
        d = Description(0, "func", "bold")

        acq = Acquisition(src_file, p, d)

        assert acq.src_file == src_file
        assert acq.participant == p
        assert acq.description == d
        assert acq.data == {}

    @pytest.mark.parametrize(
        ("src_file", "expected"),
        [
            (Path("a.json"), Path("a")),
            (Path("a.nii.gz"), Path("a")),
            (Path("a/b/c.json"), Path("a/b/c")),
            (Path("a/b/c.nii.gz"), Path("a/b/c")),
        ],
    )
    def test_src_root(self, src_file, expected):
        p = Participant("sub-01", "ses-01")
        d = Description(0, "func", "bold")

        acq = Acquisition(src_file, p, d)

        assert acq.src_root == expected

    @pytest.mark.parametrize(
        ("participant", "description", "expected_dst_root", "expected_drnm"),
        [
            (
                Participant("1"),
                Description(0, "func", "_bold"),
                Path("sub-1/func/sub-1_bold"),
                Path("sub-1/func/sub-1"),
            ),
            (
                Participant("1", "2"),
                Description(0, "perf", "_asl"),
                Path("sub-1/ses-2/perf/sub-1_ses-2_asl"),
                Path("sub-1/ses-2/perf/sub-1_ses-2"),
            ),
            (
                Participant("1"),
                Description(0, "func", "_bold", custom_labels="dir-AP_acq-test"),
                Path("sub-1/func/sub-1_acq-test_dir-AP_bold"),
                Path("sub-1/func/sub-1_acq-test_dir-AP"),
            ),
        ],
    )
    def test_dst_root_methods(
        self,
        participant,
        description,
        expected_dst_root,
        expected_drnm,
    ):
        acq = Acquisition("", participant, description)
        assert acq.dst_root == expected_dst_root
        assert acq.dst_root_no_modality == expected_drnm

    @pytest.mark.parametrize(
        ("p", "d"),
        [
            (Participant("sub-01"), Description(0, "perf", "_asl")),
            (
                Participant("sub-01", "ses-01"),
                Description(0, "func", "bold", custom_labels="echo-1_dir-ap"),
            ),
        ],
    )
    def test_equal_acquisitions(self, p, d):
        assert Acquisition(Path("a.json"), p, d) == Acquisition(Path("b.nii.gz"), p, d)

    @pytest.mark.parametrize(
        ("p1", "d1", "p2", "d2"),
        [
            (
                Participant("sub-01"),
                Description(0, "perf", "_asl"),
                Participant("sub-01", "ses-01"),
                Description(0, "func", "bold", custom_labels="echo-1_dir-ap"),
            ),
        ],
    )
    def test_non_equal_acquisitions(self, p1, d1, p2, d2):
        assert Acquisition(Path("a.json"), p1, d1) != Acquisition(
            Path("a.json"),
            p2,
            d2,
        )


class TestIntendedForResolver:
    def test_init_defaults(self):
        r = IntendedForResolver()
        assert r.logger is not None

    def test_init(self):
        logger = logging.getLogger("test123")
        logger.setLevel(level=logging.CRITICAL)
        r = IntendedForResolver(logger)

        assert r.logger is logger

    @pytest.mark.parametrize(
        ("acquisitions", "expected_IntentedFor"),
        [
            # empty acquisitions
            ([], []),
            # int intended_for, existing target
            (
                [
                    Acquisition(
                        "",
                        Participant("1"),
                        Description(12, "fmap", "fmap", intended_for=3),
                    ),
                    Acquisition("", Participant("1"), Description(3, "func", "bold")),
                ],
                ["func/sub-1_bold.nii.gz", None],
            ),
            # str intended_for, existing target
            (
                [
                    Acquisition(
                        "",
                        Participant("1", "A"),
                        Description(100, "fmap", "fmap", intended_for="desc-id"),
                    ),
                    Acquisition(
                        "",
                        Participant("1", "A"),
                        Description(21, "func", "bold", data={"id": "desc-id"}),
                    ),
                ],
                ["ses-A/func/sub-1_ses-A_bold.nii.gz", None],
            ),
            # (int | str)[] intended_for, existing targets
            (
                [
                    Acquisition(
                        "",
                        Participant("1"),
                        Description(21, "func", "bold", data={"id": "desc-id"}),
                    ),
                    Acquisition(
                        "",
                        Participant("1"),
                        Description(12, "perf", "asl"),
                    ),
                    Acquisition(
                        "",
                        Participant("1"),
                        Description(100, "fmap", "fmap", intended_for=[12, "desc-id"]),
                    ),
                ],
                # note the order of expected_IntendedFor
                [None, None, ["perf/sub-1_asl.nii.gz", "func/sub-1_bold.nii.gz"]],
            ),
            # int intended_for, non-existant target
            (
                [
                    Acquisition(
                        "",
                        Participant("1"),
                        Description(12, "fmap", "fmap", intended_for=3),
                    ),
                    Acquisition("", Participant("1"), Description(1, "func", "bold")),
                ],
                [None, None],
            ),
            # str intended_for, non-existant target
            (
                [
                    Acquisition(
                        "",
                        Participant("1", "A"),
                        Description(100, "fmap", "fmap", intended_for="desc-id"),
                    ),
                ],
                [None],
            ),
            # (int | str)[] intended_for, non-existant targets
            (
                [
                    Acquisition("", Participant("1"), Description(13, "func", "bold")),
                    Acquisition(
                        "",
                        Participant("1"),
                        Description(100, "fmap", "fmap", intended_for=[12, "desc-id"]),
                    ),
                ],
                # note the order of expected_IntendedFor
                [None, None],
            ),
        ],
    )
    def test_resolve(self, mocker: MockerFixture, acquisitions, expected_IntentedFor):
        mocker.patch("d2b.d2b.associated_nii_ext").return_value = ".nii.gz"

        resolver = IntendedForResolver()
        resolved_acqs = resolver.resolve(acquisitions)

        for acq, expected in zip(resolved_acqs, expected_IntentedFor):
            assert acq.data.get("IntendedFor") == expected

    def test_existing_target_acquisition_but_no_associated_nii_file(
        self,
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
    ):
        # associated_nii_ext finds the associated nii and returns the
        # file's extension, if no associated nii is found then we get
        # None, so we patch that function to return None to simulate
        # there not being an associated nii file.
        mocker.patch("d2b.d2b.associated_nii_ext").return_value = None

        acquisitions = [
            Acquisition(
                "a.json",
                Participant("1"),
                Description(12, "fmap", "fmap", intended_for=3),
            ),
            Acquisition(
                "target.json",
                Participant("1"),
                Description(3, "func", "bold"),
            ),
        ]

        resolver = IntendedForResolver()
        resolver.resolve(acquisitions)

        assert any(
            "No NIfTI file associated with file [target.json]." in msg
            for _, _, msg in caplog.record_tuples
        )

    def test_bad_intended_for_type_raises_ValueError(self, mocker: MockerFixture):
        mocker.patch("d2b.d2b.associated_nii_ext").return_value = ".nii.gz"

        acquisitions = [
            Acquisition(
                "a.json",
                Participant("1"),
                Description(12, "fmap", "", intended_for={"k": "v"}),  # type: ignore
            ),
        ]

        resolver = IntendedForResolver()
        with pytest.raises(ValueError):
            resolver.resolve(acquisitions)


class TestMatcher:
    def test_init(self):
        files = [Path("a.json")]
        participant = Participant("abc", "1")
        descriptions = [Description(0, "func", "bold")]
        config = {"config_key": "config_value"}
        options = {"option_key": "option_value"}
        logger = logging.getLogger("test")

        matcher = Matcher(files, participant, descriptions, config, options, logger)

        assert matcher.files == files
        assert matcher.participant == participant
        assert matcher.descriptions == descriptions
        assert matcher.config == config
        assert matcher.options == options
        assert matcher.logger == logger

    def test_init_defaults(self):
        files = [Path("a.json")]
        participant = Participant("abc", "1")
        descriptions = [Description(0, "func", "bold")]

        matcher = Matcher(files, participant, descriptions)

        assert matcher.files == files
        assert matcher.participant == participant
        assert matcher.descriptions == descriptions
        assert matcher.config == {}
        assert matcher.options == {}
        assert matcher.logger is not None and matcher.logger.name == "d2b.d2b"

    @pytest.mark.parametrize(
        # NOTE: this test relies on the implementation insofar as we "known"
        # that files and descriptions are compared via
        # itertools.produce(file, descriptions), this knowledge is reflected
        # in the 'patched_links' iterable (used to mock-out the is_link hook)
        ("files", "descriptions", "patched_links", "matched_descriptions"),
        [
            # empty everything
            ([], [], [], []),
            # empty files
            ([], [Description(0, "func", "a"), Description(0, "func", "b")], [], []),
            # empty descriptions
            ([Path("a.json"), Path("b.json")], [], [], []),
            # no matches
            (
                [Path("a.json"), Path("b.json")],
                [Description(0, "func", "a"), Description(1, "func", "b")],
                # calling the is_link hook results in a list of non-None
                # values, each entry in the following list will be used
                # to mock a call to the is_link hook
                [[False], [False], [False], [False]],
                [],
            ),
            # file matches unique description
            # - f: (matched files) -> (matched descriptions) is a bijection
            (
                [Path("a.json"), Path("b.json")],
                [
                    Description(0, "func", "a", data={"criteria": {}}),
                    Description(1, "func", "b", data={"criteria": {}}),
                ],
                [[True], [False], [False], [True]],  # a.json -> 0, b.json -> 1
                [0, 1],
            ),
            # file matches more than one description (i.e. TAKE NO ACTION)
            # - f: (matched descriptions) -> (matched files) is NON-injective
            (
                [Path("a.json"), Path("b.json")],
                [
                    Description(0, "func", "a", data={"criteria": {}}),
                    Description(1, "func", "b", data={"criteria": {}}),
                ],
                [[True], [True], [False], [False]],  # a.json -> 0, a.json -> 1
                [],
            ),
            # description matches more than one file (i.e. DUPLICATE RUNS)
            # - f: (matched files) -> (matched descriptions) is NON-injective
            (
                [Path("a.json"), Path("b.json")],
                [
                    Description(0, "func", "a", data={"criteria": {}}),
                    Description(1, "func", "b", data={"criteria": {}}),
                ],
                [[True], [False], [True], [False]],  # a.json -> 0, b.json -> 0
                [0, 0],
            ),
        ],
    )
    def test_run(
        self,
        mocker: MockerFixture,
        files,
        descriptions,
        patched_links,
        matched_descriptions,
    ):
        mocker.patch("d2b.d2b.pm").hook.is_link.side_effect = patched_links

        matcher = Matcher(files, Participant("a", "1"), descriptions)
        acquisitions = matcher.run()

        # check that we got as many matches as we expected (since we're
        # mocking is_link this is a little "self-fulfulling")
        assert len(acquisitions) == len(matched_descriptions)

        # check that each acquisition has a description object
        # that matches the description we expected
        for (acq, desc_idx) in zip(acquisitions, matched_descriptions):
            assert acq.description.index == desc_idx

        # check if run deduping happened
        if len(matched_descriptions) > 0 and len(set(matched_descriptions)) == 1:
            # more than one matched description and each matched descriptions
            # is actually the same description (i.e. the last test case above)
            for i, acq in enumerate(acquisitions, 1):
                assert f"run-{i}" in str(acq.dst_root)
        else:
            # check that no run deduping happened
            for acq in acquisitions:
                assert "run" not in str(acq.dst_root)


class TestD2b:
    def test_init(self, tmpdir: str):
        in_dirs = ["in1/", Path("in2/")]
        out_dir = Path(tmpdir) / "out"
        config_file = Path("config.json")
        subject_id = "sub-abc"
        session = "ses-123"
        options = {"a": 1}

        d2b = D2B(in_dirs, out_dir, config_file, subject_id, session, options)

        assert d2b.in_dirs == list(map(Path, in_dirs))
        assert d2b.out_dir == Path(out_dir)
        assert d2b.config_file == config_file
        assert d2b.participant == Participant(subject_id, session)
        assert d2b.options == options

    def test_load_config(self, mocker: MockerFixture, tmpdir: str):
        load_config_mock = mocker.patch("d2b.d2b.pm").hook.load_config

        d2b = D2B([], tmpdir, "c.json", "a")
        d2b.load_config()

        # check that load config called the associated hook
        load_config_mock.assert_called_once_with(path=Path("c.json"), d2b=d2b)

    def _check_run_results(
        self,
        data_dir: Path,
        out_dir: Path,
        sidecar_files: list[str],
        other_files: list[str],
    ):
        """generic checks for all test_run_* methods"""
        config_file = data_dir / "d2b-config.json"
        in_dirs = [data_dir / "in"]

        expected_out_dir = data_dir / "out"

        d2b = D2B(in_dirs, out_dir, config_file, "a", "1")
        d2b.load_config()
        d2b.run()

        for f in sidecar_files:
            assert (out_dir / f).exists()

            actual_sidecar = json.loads((out_dir / f).read_text())
            expected_sidecar = json.loads((expected_out_dir / f).read_text())
            assert actual_sidecar.pop("D2bVersion") == __version__
            assert actual_sidecar == expected_sidecar

        for f in other_files:
            assert (out_dir / f).exists()
            assert filecmp.cmp(out_dir / f, expected_out_dir / f, shallow=False)

    def test_run_extra_files(self, d2b_run_e2e: Path, tmpdir: str):
        # test-specific
        data_dir = d2b_run_e2e / "extra-files"
        sidecar_files = [
            "sub-a/ses-1/dwi/sub-a_ses-1_dwi.json",
        ]
        other_files = [
            "sub-a/ses-1/dwi/sub-a_ses-1_dwi.bval",
            "sub-a/ses-1/dwi/sub-a_ses-1_dwi.bvec",
            "sub-a/ses-1/dwi/sub-a_ses-1_dwi.nii.gz",
            "sub-a/ses-1/dwi/sub-a_ses-1_dwi.txt",
        ]
        out_dir = Path(tmpdir) / "bids"

        self._check_run_results(data_dir, out_dir, sidecar_files, other_files)

    def test_run_intended_for_fields(self, d2b_run_e2e: Path, tmpdir: str):
        # test-specific
        data_dir = d2b_run_e2e / "intended-for-fields"
        sidecar_files = [
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-AP_fmap.json",
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-PA_fmap.json",
            "sub-a/ses-1/fmap/sub-a_ses-1_fmap.json",
            "sub-a/ses-1/func/sub-a_ses-1_task-rest_bold.json",
            "sub-a/ses-1/anat/sub-a_ses-1_T1w.json",
            "sub-a/ses-1/func/sub-a_ses-1_task-fingertap_bold.json",
        ]
        other_files = [
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-AP_fmap.nii.gz",
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-PA_fmap.nii.gz",
            "sub-a/ses-1/fmap/sub-a_ses-1_fmap.nii.gz",
            "sub-a/ses-1/func/sub-a_ses-1_task-rest_bold.nii.gz",
            "sub-a/ses-1/anat/sub-a_ses-1_T1w.nii.gz",
            "sub-a/ses-1/func/sub-a_ses-1_task-fingertap_bold.nii.gz",
        ]
        out_dir = Path(tmpdir) / "bids"

        self._check_run_results(data_dir, out_dir, sidecar_files, other_files)

    def test_run_intended_for_no_target(self, d2b_run_e2e: Path, tmpdir: str):
        # test-specific
        data_dir = d2b_run_e2e / "intended-for-no-target"
        sidecar_files = ["sub-a/ses-1/fmap/sub-a_ses-1_dir-AP_fmap.json"]
        other_files = ["sub-a/ses-1/fmap/sub-a_ses-1_dir-AP_fmap.nii.gz"]
        out_dir = Path(tmpdir) / "bids"

        self._check_run_results(data_dir, out_dir, sidecar_files, other_files)

    def test_run_intended_for_target_has_run(self, d2b_run_e2e: Path, tmpdir: str):
        # test-specific
        data_dir = d2b_run_e2e / "intended-for-target-has-run"
        sidecar_files = [
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-AP_fmap.json",
            "sub-a/ses-1/func/sub-a_ses-1_task-rest_run-1_bold.json",
            "sub-a/ses-1/func/sub-a_ses-1_task-rest_run-2_bold.json",
        ]
        other_files = [
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-AP_fmap.nii.gz",
            "sub-a/ses-1/func/sub-a_ses-1_task-rest_run-1_bold.nii.gz",
            "sub-a/ses-1/func/sub-a_ses-1_task-rest_run-2_bold.nii.gz",
        ]
        out_dir = Path(tmpdir) / "bids"

        self._check_run_results(data_dir, out_dir, sidecar_files, other_files)

    def test_run_intended_for_list_target_has_run(self, d2b_run_e2e: Path, tmpdir: str):
        # test-specific
        data_dir = d2b_run_e2e / "intended-for-list-target-has-run"
        sidecar_files = [
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-AP_fmap.json",
            "sub-a/ses-1/func/sub-a_ses-1_task-rest_run-1_bold.json",
            "sub-a/ses-1/func/sub-a_ses-1_task-rest_run-2_bold.json",
            "sub-a/ses-1/dwi/sub-a_ses-1_dwi.json",
        ]
        other_files = [
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-AP_fmap.nii.gz",
            "sub-a/ses-1/func/sub-a_ses-1_task-rest_run-1_bold.nii.gz",
            "sub-a/ses-1/func/sub-a_ses-1_task-rest_run-2_bold.nii.gz",
            "sub-a/ses-1/dwi/sub-a_ses-1_dwi.nii.gz",
        ]
        out_dir = Path(tmpdir) / "bids"

        self._check_run_results(data_dir, out_dir, sidecar_files, other_files)

    def test_run_no_associated_nii(
        self,
        d2b_run_e2e: Path,
        tmpdir: str,
        caplog: LogCaptureFixture,
    ):
        data_dir = d2b_run_e2e / "no-associated-nii"
        config_file = data_dir / "d2b-config.json"
        in_dirs = [data_dir / "in"]
        out_dir = Path(tmpdir) / "bids"

        d2b = D2B(in_dirs, out_dir, config_file, "a", "1")
        d2b.load_config()
        d2b.run()

        session_dir = out_dir / "sub-a/ses-1"
        assert session_dir.exists()
        assert len(list(session_dir.rglob("*.json"))) == 1
        assert len(list(session_dir.rglob("*.nii.gz"))) == 0

        messagesubstr = (
            "No associated nii found for acquisition derived from file [t1.json]"
        )
        assert _produced_log(caplog, logging.WARNING, messagesubstr)

    def test_run_no_matches(
        self,
        d2b_run_e2e: Path,
        tmpdir: str,
        caplog: LogCaptureFixture,
    ):
        data_dir = d2b_run_e2e / "no-matches"
        config_file = data_dir / "d2b-config.json"
        in_dirs = [data_dir / "in"]
        out_dir = Path(tmpdir) / "bids"

        d2b = D2B(in_dirs, out_dir, config_file, "a", "1")
        d2b.load_config()
        d2b.run()

        session_dir = out_dir / "sub-a/ses-1"
        assert not session_dir.exists()
        assert len(list(session_dir.rglob("*.json"))) == 0
        assert len(list(session_dir.rglob("*..nii.gz"))) == 0

        messagesubstr = "NO DESCRIPTIONS MATCHED ANY FILES"
        assert _produced_log(caplog, logging.WARNING, messagesubstr)

    def test_run_non_gzipped(self, d2b_run_e2e: Path, tmpdir: str):
        # test-specific
        data_dir = d2b_run_e2e / "non-gzipped"
        sidecar_files = [
            "sub-a/ses-1/anat/sub-a_ses-1_T1w.json",
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-AP_fmap.json",
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-PA_fmap.json",
            "sub-a/ses-1/fmap/sub-a_ses-1_fmap.json",
            "sub-a/ses-1/func/sub-a_ses-1_task-fingertap_bold.json",
            "sub-a/ses-1/func/sub-a_ses-1_task-rest_bold.json",
        ]
        other_files = [
            "sub-a/ses-1/anat/sub-a_ses-1_T1w.nii.gz",
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-AP_fmap.nii",
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-PA_fmap.nii",
            "sub-a/ses-1/fmap/sub-a_ses-1_fmap.nii.gz",
            "sub-a/ses-1/func/sub-a_ses-1_task-fingertap_bold.nii",
            "sub-a/ses-1/func/sub-a_ses-1_task-rest_bold.nii",
        ]
        out_dir = Path(tmpdir) / "bids"

        self._check_run_results(data_dir, out_dir, sidecar_files, other_files)

    def test_run_one_file_multi_desc(
        self,
        d2b_run_e2e: Path,
        tmpdir: str,
        caplog: LogCaptureFixture,
    ):
        data_dir = d2b_run_e2e / "one-file-multi-desc"
        config_file = data_dir / "d2b-config.json"
        in_dirs = [data_dir / "in"]
        out_dir = Path(tmpdir) / "bids"

        d2b = D2B(in_dirs, out_dir, config_file, "a", "1")
        d2b.load_config()
        d2b.run()

        assert _produced_log(
            caplog,
            logging.WARNING,
            "matched [2] descriptions. Skipping. Matching descriptions [0, 1]",
        )
        assert _produced_log(
            caplog,
            logging.WARNING,
            "description [0] dataType [anat] modality [_T1w]",
        )
        assert _produced_log(
            caplog,
            logging.WARNING,
            "description [1] dataType [anat] modality [_T1w]",
        )
        ses_dir = out_dir / "sub-a/ses-1"
        assert not (ses_dir).exists()
        assert len(list(f for f in (ses_dir).rglob("*") if f.is_file())) == 0

    def test_run_sidecar_changes(self, d2b_run_e2e: Path, tmpdir: str):
        # test-specific
        data_dir = d2b_run_e2e / "non-gzipped"
        sidecar_files = ["sub-a/ses-1/anat/sub-a_ses-1_T1w.json"]
        other_files = ["sub-a/ses-1/anat/sub-a_ses-1_T1w.nii.gz"]
        out_dir = Path(tmpdir) / "bids"

        self._check_run_results(data_dir, out_dir, sidecar_files, other_files)


def _produced_log(caplog: LogCaptureFixture, levelno: int, messagesubstr: str) -> bool:
    return any(
        r for r in caplog.records if r.levelno == levelno and messagesubstr in r.message
    )
