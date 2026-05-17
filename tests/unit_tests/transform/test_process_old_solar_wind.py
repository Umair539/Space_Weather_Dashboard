from src.transform.process_old_solar_wind import (
    filter_columns,
    format_column_names,
    drop_duplicates,
    set_time_index,
)

import pandas as pd


class TestFilterColumns:
    def test_filter_columns(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "bz_gsm": 1.5,
                    "bx_gsm": 0.5,
                    "by_gsm": 0.3,
                    "bt": 2.0,
                    "extra_col": 99,
                }
            ]
        )
        result = filter_columns(df, ["bz_gsm", "bx_gsm", "by_gsm", "bt"])
        assert list(result.columns) == ["time_tag", "bz_gsm", "bx_gsm", "by_gsm", "bt"]


class TestFormatColumnNames:
    def test_format_column_names(self):
        df = pd.DataFrame([{"bz_gsm": 1.5, "bx_gsm": 0.5, "by_gsm": 0.3}])
        result = format_column_names(
            df, {"bz_gsm": "bz", "bx_gsm": "bx", "by_gsm": "by"}
        )
        assert list(result.columns) == ["bz", "bx", "by"]


class TestDropDuplicates:
    def test_drop_duplicates(self):
        df = pd.DataFrame(
            [
                {"time_tag": "2026-01-01T00:00:00", "bz_gsm": 1.5},
                {"time_tag": "2026-01-01T00:00:00", "bz_gsm": 1.5},
            ]
        )
        result = drop_duplicates(df)
        assert len(result) == 1


class TestSetTimeIndex:
    def test_set_time_index(self):
        df = pd.DataFrame([{"time_tag": "2026-01-01T00:00:00", "bz_gsm": 1.5}])
        result = set_time_index(df)
        assert str(result.index.dtype) == "datetime64[ns]"
        assert "time_tag" not in result.columns
