import pytest
from src.utils.validator import validate_schema, SchemaError


class TestValidateSchema:
    def test_valid_list_of_dicts_passes(self):
        data = [{"time_tag": "2026-01-01T00:00:00", "dst": -5}]
        validate_schema("dst", data)

    def test_valid_list_of_lists_passes(self):
        data = [
            ["time_tag", "Kp"],
            ["2026-01-01T00:00:00", 2.0],
        ]
        validate_schema("kp", data)

    def test_extra_columns_allowed(self):
        data = [
            {
                "time_tag": "2026-01-01T00:00:00",
                "dst": -5,
                "some_new_noaa_field": "whatever",
            }
        ]
        validate_schema("dst", data)

    def test_missing_required_column_raises(self):
        data = [{"time_tag": "2026-01-01T00:00:00"}]
        with pytest.raises(SchemaError, match="missing"):
            validate_schema("dst", data)

    def test_empty_payload_raises(self):
        with pytest.raises(SchemaError, match="empty"):
            validate_schema("dst", [])

    def test_none_payload_raises(self):
        with pytest.raises(SchemaError, match="empty"):
            validate_schema("dst", None)

    def test_error_message_includes_diagnostic_info(self):
        data = [{"time_tag": "2026-01-01T00:00:00"}]
        with pytest.raises(SchemaError) as exc_info:
            validate_schema("dst", data)
        msg = str(exc_info.value)
        assert "dst" in msg
        assert "missing" in msg
        assert "received" in msg
