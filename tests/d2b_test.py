from d2b import FilenameEntities


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
