from pathlib import Path

import pytest
from d2b.d2b import Acquisition
from d2b.d2b import Description
from d2b.d2b import FilenameEntities
from d2b.d2b import Participant


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
        acq = Acquisition(Path(), participant, description)
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

    # def test_init_custom_params(self):
    #     p = Participant("label01", "session01")
    #     s = Sidecar("a/b.json", {"a": 1, "b": 2})
    #     d = "anat"

    #     acq = Acquisition(
    #         p,
    #         s,
    #         d,
    #         "T1w",
    #         "task-rest_desc-something",
    #         {"a": -1, "c": "hello"},
    #         1,
    #     )

    #     assert acq.participant == p
    #     assert acq.sidecar == s
    #     assert acq.data_type == d
    #     assert acq.modality_label == "_T1w"

    #     assert acq.custom_labels == "_task-rest_desc-something"
    #     assert acq.sidecar_changes == {"a": -1, "c": "hello"}
    #     assert acq.intended_for == 1
    #     assert acq.suffix == "_task-rest_desc-something_T1w"
    #     assert acq.src_root == Path("a/b")
    #     assert acq.dst_root == Path(
    #         "sub-label01",
    #         "ses-session01",
    #         "anat",
    #         "sub-label01_ses-session01_task-rest_desc-something_T1w",
    #     )

    # def test_init_custom_params_variant2(self):
    #     p = Participant("label01", "session01")
    #     s = Sidecar("a/b.json", {"a": 1, "b": 2})
    #     d = "anat"

    #     acq = Acquisition(
    #         p,
    #         s,
    #         d,
    #         "T1w",
    #         {"task": "rest", "desc": "something"},
    #         {"a": -1, "c": "hello"},
    #         [2, 3],
    #     )

    #     assert acq.participant == p
    #     assert acq.sidecar == s
    #     assert acq.data_type == d
    #     assert acq.modality_label == "_T1w"

    #     assert acq.custom_labels == "_task-rest_desc-something"
    #     assert acq.sidecar_changes == {"a": -1, "c": "hello"}
    #     assert acq.intended_for == [2, 3]
    #     assert acq.suffix == "_task-rest_desc-something_T1w"
    #     assert acq.src_root == Path("a/b")
    #     assert acq.dst_root == Path(
    #         "sub-label01",
    #         "ses-session01",
    #         "anat",
    #         "sub-label01_ses-session01_task-rest_desc-something_T1w",
    #     )

    # def test_acqs_with_same_params_are_equal(self):
    #     acq1 = Acquisition(
    #         Participant("label01", "session01"),
    #         Sidecar("a/b.json", {"a": 1, "b": 2}),
    #         "anat",
    #         "T1w",
    #     )

    #     acq2 = Acquisition(
    #         Participant("label01", "session01"),
    #         Sidecar("a/b.json", {"a": 1, "b": 2}),
    #         "anat",
    #         "T1w",
    #     )

    #     assert acq1 == acq2


# class TestDcm2niix:
#     def test_init_with_defaults(self):
#         d2n = Dcm2niix("a/in/", "b/out/")

#         assert d2n.dcm_dir == Path("a/in/")
#         assert d2n.nii_dir == Path("b/out/")
#         assert d2n.options == {}
#         assert d2n.subprocess_run_kwargs == {
#             "check": True,
#             "text": True,
#             "capture_output": True,
#         }

#     def test_init(self):
#         d2n = Dcm2niix("a/in/", "b/out/", {"--option": "opt-val", "-a": "b"})

#         assert d2n.dcm_dir == Path("a/in/")
#         assert d2n.nii_dir == Path("b/out/")
#         assert d2n.options == {"--option": "opt-val", "-a": "b"}

#     def test_run_with_defaults(self, mocker: MockerFixture):
#         sp_run_mock = mocker.patch("subprocess.run")

#         d2n = Dcm2niix("a/in/", "b/out/")

#         d2n.run()

#         assert d2n.completed_process
#         sp_run_mock.assert_called_with(
#             ("dcm2niix", "-o", "b/out", "a/in"),
#             check=True,
#             text=True,
#             capture_output=True,
#         )

#     def test_run(self, mocker: MockerFixture):
#         sp_run_mock = mocker.patch("subprocess.run")

#         d2n = Dcm2niix(
#             "a/in/",
#             "b/out/",
#             {"-a": "1", "-b": "value with space"},
#             {"check": False},
#         )

#         d2n.run()

#         assert d2n.completed_process
#         sp_run_mock.assert_called_with(
#             ("dcm2niix", "-a", "1", "-b", "value with space", "-o", "b/out", "a/in"),
#             check=False,
#         )

#     def test_help(self, mocker: MockerFixture):
#         help_text = "Stuff\nMore stuff v0.0.0\nBlah"
#         sp_run_mock = mocker.patch("subprocess.run")
#         sp_run_mock.return_value.stdout = help_text

#         res = Dcm2niix.help()

#         assert isinstance(res, str) and res == help_text
#         sp_run_mock.assert_called_with(
#             ("dcm2niix",),
#             text=True,
#             capture_output=True,
#         )

#     def test_version(self, mocker: MockerFixture):
#         sp_run_mock = mocker.patch("subprocess.run")
#         sp_run_mock.return_value.stdout = "Stuff\nMore stuff v0.0.0\nBlah"

#         version = Dcm2niix.version()

#         assert version == "v0.0.0"
#         sp_run_mock.assert_called_with(
#             ("dcm2niix",),
#             text=True,
#             capture_output=True,
#         )
