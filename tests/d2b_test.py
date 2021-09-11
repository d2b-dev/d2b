import pytest
from d2b.d2b import Description
from d2b.d2b import FilenameEntities


class TestFilenameEntities:
    def test_init(self):
        entities = {"acq": "2", "sub": "1"}  # note the wrong order
        fe = FilenameEntities(entities)
        assert fe.entities == entities
        assert str(fe) == "sub-1_acq-2"
        assert list(fe) == [("sub", "1"), ("acq", "2")]

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
        entities = "_acq-2_sub-abc123"  # note the wrong order
        fe = FilenameEntities.from_string(entities)
        assert fe.entities == {"acq": "2", "sub": "abc123"}
        assert str(fe) == "sub-abc123_acq-2"
        assert list(fe) == [("sub", "abc123"), ("acq", "2")]

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


# class TestParticipant:
#     def test_init_with_one_argument(self):
#         participant = Participant("label01")
#         assert participant.label == "label01"
#         assert participant.bids_label == "sub-label01"
#         assert participant.session == ""
#         assert participant.bids_session == ""
#         assert participant.prefix == "sub-label01"
#         assert participant.directory == Path("sub-label01")

#     def test_init_with_explicit_empty_session(self):
#         participant = Participant("label01", "")
#         assert participant.label == "label01"
#         assert participant.bids_label == "sub-label01"
#         assert participant.session == ""
#         assert participant.bids_session == ""
#         assert participant.prefix == "sub-label01"
#         assert participant.directory == Path("sub-label01")

#     def test_init_with_label_and_session(self):
#         participant = Participant("label01", "session01")
#         assert participant.label == "label01"
#         assert participant.bids_label == "sub-label01"
#         assert participant.session == "session01"
#         assert participant.bids_session == "ses-session01"
#         assert participant.prefix == "sub-label01_ses-session01"
#         assert participant.directory == Path("sub-label01", "ses-session01")

#     def test_init_with_label_and_session_that_already_have_prefixes_is_ok(self):
#         participant = Participant("sub-label01", "ses-session01")
#         assert participant.label == "label01"
#         assert participant.bids_label == "sub-label01"
#         assert participant.session == "session01"
#         assert participant.bids_session == "ses-session01"
#         assert participant.prefix == "sub-label01_ses-session01"
#         assert participant.directory == Path("sub-label01", "ses-session01")

#     def test_label_and_session_are_stripped_of_whitespace(self):
#         participant = Participant(" label01 ", " session01 ")
#         assert participant.label == "label01"
#         assert participant.bids_label == "sub-label01"
#         assert participant.session == "session01"
#         assert participant.bids_session == "ses-session01"

#     def test_raises_ValueError_if_label_is_empty(self):
#         with pytest.raises(ValueError):
#             Participant("")

#     def test_raises_ValueError_if_label_is_not_alphanumeric(self):
#         with pytest.raises(ValueError):
#             Participant("label_01")

#     def test_raises_ValueError_if_session_is_not_alphanumeric(self):
#         with pytest.raises(ValueError):
#             Participant("label", "session-01")

#     def test_repr(self):
#         participant = Participant("label01", "session01")
#         assert str(participant) == "Participant('label01', 'session01')"

#     def test_repr_empty_session(self):
#         participant = Participant("label01")
#         assert str(participant) == "Participant('label01', '')"


# class TestSidecar:
#     def test_init(self):
#         filename = "a/b.json"
#         data = {"a": 1, "b": 2}
#         comp_keys = ["a", "b"]

#         sidecar = Sidecar(filename, data, comp_keys)

#         assert sidecar.filename == Path(filename)
#         assert sidecar.data == data
#         assert sidecar.comp_keys == comp_keys
#         assert sidecar.root == Path("a/b")

#     def test_init_with_defaults(self):
#         sidecar = Sidecar("a.json")

#         assert sidecar.filename == Path("a.json")
#         assert sidecar.data == {}
#         assert sidecar.comp_keys == DEFAULT.comp_keys

#     def test_is_hashable(self):
#         sidecar = Sidecar("")

#         assert hash(sidecar)

#     def test_create_from_filename(self, tmpdir):
#         data = {"a": 1, "b": 2}
#         comp_keys = ["a", "b"]
#         sidecar_path = Path(tmpdir) / "t.json"
#         sidecar_path.write_text(json.dumps(data))

#         sidecar = Sidecar.from_filename(sidecar_path, comp_keys)

#         assert sidecar.filename == sidecar_path
#         assert sidecar.data == data
#         assert sidecar.comp_keys == comp_keys

#     def test_sidecars_with_same_attrs_are_equal(self):
#         s1 = Sidecar("a.json")
#         s2 = Sidecar("a.json")

#         assert s1 == s2

#     @pytest.mark.parametrize(
#         ("s1", "s2", "s1_lt_s2"),
#         [
#             (Sidecar("a.json"), Sidecar("a.json"), False),
#             (Sidecar("a.json"), Sidecar("b.json"), True),
#             (
#                 Sidecar("a.json", {"SeriesNumber": 2}),
#                 Sidecar("b.json", {"SeriesNumber": 1}),
#                 False,
#             ),
#             (
#                 Sidecar(
#                     "b.json",
#                     {"SeriesNumber": 1, "AcquisitionTime": "12:00:00.000000"},
#                 ),
#                 Sidecar(
#                     "a.json",
#                     {"SeriesNumber": 1, "AcquisitionTime": "10:36:51.567500"},
#                 ),
#                 False,
#             ),
#             (
#                 Sidecar("a.json", {"SeriesNumber": 1, "AcquisitionTime": ""}),
#                 Sidecar("b.json", {"SeriesNumber": 1, "AcquisitionTime": ""}),
#                 True,
#             ),
#         ],
#     )
#     def test_sidecar_comparability_with_default_comp_keys(self, s1, s2, s1_lt_s2):
#         assert (s1 < s2) is s1_lt_s2


# class TestAcquisition:
#     def test_init_defaults(self):
#         p = Participant("label01", "session01")
#         s = Sidecar("a/b.json", {"a": 1, "b": 2})
#         d = "anat"
#         m = "T1w"

#         acq = Acquisition(p, s, d, m)

#         assert acq.participant == p
#         assert acq.sidecar == s
#         assert acq.data_type == d
#         assert acq.modality_label == "_T1w"

#         assert acq.custom_labels == ""
#         assert acq.sidecar_changes == {}
#         assert acq.intended_for is None
#         assert acq.suffix == "_T1w"
#         assert acq.src_root == Path("a/b")
#         assert acq.dst_root == Path(
#             "sub-label01/ses-session01/anat/sub-label01_ses-session01_T1w",
#         )

#     def test_init_custom_params(self):
#         p = Participant("label01", "session01")
#         s = Sidecar("a/b.json", {"a": 1, "b": 2})
#         d = "anat"

#         acq = Acquisition(
#             p,
#             s,
#             d,
#             "T1w",
#             "task-rest_desc-something",
#             {"a": -1, "c": "hello"},
#             1,
#         )

#         assert acq.participant == p
#         assert acq.sidecar == s
#         assert acq.data_type == d
#         assert acq.modality_label == "_T1w"

#         assert acq.custom_labels == "_task-rest_desc-something"
#         assert acq.sidecar_changes == {"a": -1, "c": "hello"}
#         assert acq.intended_for == 1
#         assert acq.suffix == "_task-rest_desc-something_T1w"
#         assert acq.src_root == Path("a/b")
#         assert acq.dst_root == Path(
#             "sub-label01",
#             "ses-session01",
#             "anat",
#             "sub-label01_ses-session01_task-rest_desc-something_T1w",
#         )

#     def test_init_custom_params_variant2(self):
#         p = Participant("label01", "session01")
#         s = Sidecar("a/b.json", {"a": 1, "b": 2})
#         d = "anat"

#         acq = Acquisition(
#             p,
#             s,
#             d,
#             "T1w",
#             {"task": "rest", "desc": "something"},
#             {"a": -1, "c": "hello"},
#             [2, 3],
#         )

#         assert acq.participant == p
#         assert acq.sidecar == s
#         assert acq.data_type == d
#         assert acq.modality_label == "_T1w"

#         assert acq.custom_labels == "_task-rest_desc-something"
#         assert acq.sidecar_changes == {"a": -1, "c": "hello"}
#         assert acq.intended_for == [2, 3]
#         assert acq.suffix == "_task-rest_desc-something_T1w"
#         assert acq.src_root == Path("a/b")
#         assert acq.dst_root == Path(
#             "sub-label01",
#             "ses-session01",
#             "anat",
#             "sub-label01_ses-session01_task-rest_desc-something_T1w",
#         )

#     def test_acqs_with_same_params_are_equal(self):
#         acq1 = Acquisition(
#             Participant("label01", "session01"),
#             Sidecar("a/b.json", {"a": 1, "b": 2}),
#             "anat",
#             "T1w",
#         )

#         acq2 = Acquisition(
#             Participant("label01", "session01"),
#             Sidecar("a/b.json", {"a": 1, "b": 2}),
#             "anat",
#             "T1w",
#         )

#         assert acq1 == acq2


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
