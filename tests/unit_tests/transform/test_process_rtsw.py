from src.transform.process_rtsw import (
    filter_columns,
    filter_to_minute,
    filter_source,
    format_column_names,
    drop_extra_cols,
    drop_duplicates,
    set_time_index,
    combine_dataframes,
    match_time_index,
    join_mag_plasma,
    cast_to_float,
    filter_invalid_data,
    filter_outliers,
    handle_missing_data,
    add_pressure_column,
    round_values,
    set_index_name,
    EXTRA_COLS,
)

import pandas as pd
import numpy as np


class TestFilterColumns:
    def test_filter_columns_mag(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-05-17T21:54:00",
                    "active": True,
                    "source": "ACE",
                    "range": None,
                    "scale": None,
                    "sensitivity": None,
                    "manual_mode": False,
                    "sample_size": 60,
                    "bt": 3.65,
                    "bx_gse": 2.66,
                    "by_gse": 2.4,
                    "bz_gse": 0.7,
                    "theta_gse": 11.05,
                    "phi_gse": 42.15,
                    "bx_gsm": 2.67,
                    "by_gsm": 1.9,
                    "bz_gsm": 1.61,
                    "theta_gsm": 26.09,
                    "phi_gsm": 35.43,
                    "max_telemetry_flag": 0,
                    "max_data_flag": 0,
                    "overall_quality": 0,
                }
            ]
        )
        result = filter_columns(
            df, ["bz_gsm", "bx_gsm", "by_gsm", "bt"], extra_cols=EXTRA_COLS
        )
        assert list(result.columns) == [
            "time_tag",
            "active",
            "source",
            "bz_gsm",
            "bx_gsm",
            "by_gsm",
            "bt",
        ]

    def test_filter_columns_plasma(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-05-17T21:56:00",
                    "active": False,
                    "source": "DSCOVR",
                    "proton_speed": 516,
                    "proton_temperature": 79712,
                    "proton_density": 3.34,
                    "proton_vx_gse": -514.4,
                    "proton_vy_gse": 5.3,
                    "proton_vz_gse": -40.4,
                    "proton_vx_gsm": -514.4,
                    "proton_vy_gsm": 20.5,
                    "proton_vz_gsm": -35.2,
                    "proton_sample_size": 10,
                    "alpha_speed": None,
                    "alpha_temperature": None,
                    "alpha_density": None,
                    "alpha_vx_gse": None,
                    "alpha_vy_gse": None,
                    "alpha_vz_gse": None,
                    "alpha_vx_gsm": None,
                    "alpha_vy_gsm": None,
                    "alpha_vz_gsm": None,
                    "alpha_sample_size": None,
                    "max_convergence_flag": 0,
                    "max_data_flag": 1,
                    "max_error_count_flag": 0,
                    "max_processing_flag": 0,
                    "max_range_flag": 0,
                    "max_sample_count_flag": 0,
                    "max_telemetry_flag": 0,
                    "overall_quality": 0,
                }
            ]
        )
        result = filter_columns(
            df,
            ["proton_speed", "proton_temperature", "proton_density"],
            extra_cols=EXTRA_COLS,
        )
        assert list(result.columns) == [
            "time_tag",
            "active",
            "source",
            "proton_speed",
            "proton_temperature",
            "proton_density",
        ]

    def test_filter_columns_no_extra_cols(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "bz_gsm": 1.5,
                    "bt": 2.0,
                    "extra": 99,
                }
            ]
        )
        result = filter_columns(df, ["bz_gsm", "bt"])
        assert list(result.columns) == ["time_tag", "bz_gsm", "bt"]


class TestFilterToMinute:
    def test_drops_rows_with_nonzero_seconds(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:02",
                    "active": False,
                    "source": "IMAP",
                    "bz_gsm": 1.0,
                },
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": False,
                    "source": "SOLAR1",
                    "bz_gsm": 2.0,
                },
            ]
        )
        result = filter_to_minute(df)
        assert len(result) == 1
        assert result["time_tag"].iloc[0] == "2026-01-01T00:00:00"

    def test_keeps_rows_with_zero_seconds(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": False,
                    "source": "SOLAR1",
                    "bz_gsm": 1.0,
                },
                {
                    "time_tag": "2026-01-01T00:01:00",
                    "active": False,
                    "source": "ACE",
                    "bz_gsm": 2.0,
                },
            ]
        )
        result = filter_to_minute(df)
        assert len(result) == 2

    def test_empty_when_all_nonzero_seconds(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:02",
                    "active": False,
                    "source": "IMAP",
                    "bz_gsm": 1.0,
                },
                {
                    "time_tag": "2026-01-01T00:01:02",
                    "active": False,
                    "source": "IMAP",
                    "bz_gsm": 2.0,
                },
            ]
        )
        result = filter_to_minute(df)
        assert len(result) == 0


class TestFilterSource:
    def test_keeps_active_row_when_valid(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": True,
                    "source": "SOLAR1",
                    "bz_gsm": 1.5,
                    "bt": 2.0,
                    "bx_gsm": 0.5,
                    "by_gsm": 0.3,
                },
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": False,
                    "source": "SOLAR1",
                    "bz_gsm": 9.9,
                    "bt": 9.9,
                    "bx_gsm": 9.9,
                    "by_gsm": 9.9,
                },
            ]
        )
        result = filter_source(df, ["bz_gsm", "bt", "bx_gsm", "by_gsm"])
        assert (
            result.loc[result["time_tag"] == "2026-01-01T00:00:00", "bz_gsm"].iloc[0]
            == 1.5
        )

    def test_replaces_active_with_inactive_when_active_all_nan(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": True,
                    "source": "SOLAR1",
                    "bz_gsm": None,
                    "bt": None,
                    "bx_gsm": None,
                    "by_gsm": None,
                },
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": False,
                    "source": "SOLAR1",
                    "bz_gsm": 9.9,
                    "bt": 9.9,
                    "bx_gsm": 9.9,
                    "by_gsm": 9.9,
                },
            ]
        )
        result = filter_source(df, ["bz_gsm", "bt", "bx_gsm", "by_gsm"])
        assert (
            result.loc[result["time_tag"] == "2026-01-01T00:00:00", "bz_gsm"].iloc[0]
            == 9.9
        )

    def test_keeps_active_when_both_nan(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": True,
                    "source": "SOLAR1",
                    "bz_gsm": None,
                    "bt": None,
                    "bx_gsm": None,
                    "by_gsm": None,
                },
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": False,
                    "source": "SOLAR1",
                    "bz_gsm": None,
                    "bt": None,
                    "bx_gsm": None,
                    "by_gsm": None,
                },
            ]
        )
        result = filter_source(df, ["bz_gsm", "bt", "bx_gsm", "by_gsm"])
        assert len(result[result["time_tag"] == "2026-01-01T00:00:00"]) == 1

    def test_includes_inactive_only_timestamp(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:01:00",
                    "active": False,
                    "source": "SOLAR1",
                    "bz_gsm": 3.0,
                    "bt": 3.0,
                    "bx_gsm": 3.0,
                    "by_gsm": 3.0,
                },
            ]
        )
        result = filter_source(df, ["bz_gsm", "bt", "bx_gsm", "by_gsm"])
        assert len(result[result["time_tag"] == "2026-01-01T00:01:00"]) == 1

    def test_two_active_rows_picks_higher_priority(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": True,
                    "source": "ACE",
                    "bz_gsm": 9.9,
                    "bt": 9.9,
                    "bx_gsm": 9.9,
                    "by_gsm": 9.9,
                },
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": True,
                    "source": "SOLAR1",
                    "bz_gsm": 1.5,
                    "bt": 2.0,
                    "bx_gsm": 0.5,
                    "by_gsm": 0.3,
                },
            ]
        )
        result = filter_source(df, ["bz_gsm", "bt", "bx_gsm", "by_gsm"])
        assert len(result[result["time_tag"] == "2026-01-01T00:00:00"]) == 1
        assert (
            result.loc[result["time_tag"] == "2026-01-01T00:00:00", "bz_gsm"].iloc[0]
            == 1.5
        )

    def test_two_inactive_rows_no_active_picks_higher_priority(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": False,
                    "source": "ACE",
                    "bz_gsm": 9.9,
                    "bt": 9.9,
                    "bx_gsm": 9.9,
                    "by_gsm": 9.9,
                },
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": False,
                    "source": "SOLAR1",
                    "bz_gsm": 1.5,
                    "bt": 2.0,
                    "bx_gsm": 0.5,
                    "by_gsm": 0.3,
                },
            ]
        )
        result = filter_source(df, ["bz_gsm", "bt", "bx_gsm", "by_gsm"])
        assert len(result[result["time_tag"] == "2026-01-01T00:00:00"]) == 1
        assert (
            result.loc[result["time_tag"] == "2026-01-01T00:00:00", "bz_gsm"].iloc[0]
            == 1.5
        )

    def test_active_nan_multiple_inactive_picks_highest_priority_valid(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": True,
                    "source": "SOLAR1",
                    "bz_gsm": None,
                    "bt": None,
                    "bx_gsm": None,
                    "by_gsm": None,
                },
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": False,
                    "source": "ACE",
                    "bz_gsm": 9.9,
                    "bt": 9.9,
                    "bx_gsm": 9.9,
                    "by_gsm": 9.9,
                },
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": False,
                    "source": "DSCOVR",
                    "bz_gsm": 5.5,
                    "bt": 5.5,
                    "bx_gsm": 5.5,
                    "by_gsm": 5.5,
                },
            ]
        )
        result = filter_source(df, ["bz_gsm", "bt", "bx_gsm", "by_gsm"])
        assert len(result[result["time_tag"] == "2026-01-01T00:00:00"]) == 1
        assert (
            result.loc[result["time_tag"] == "2026-01-01T00:00:00", "bz_gsm"].iloc[0]
            == 9.9
        )

    def test_higher_priority_inactive_nan_falls_back_to_lower_priority_valid(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": False,
                    "source": "SOLAR1",
                    "bz_gsm": None,
                    "bt": None,
                    "bx_gsm": None,
                    "by_gsm": None,
                },
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": False,
                    "source": "ACE",
                    "bz_gsm": 9.9,
                    "bt": 9.9,
                    "bx_gsm": 9.9,
                    "by_gsm": 9.9,
                },
            ]
        )
        result = filter_source(df, ["bz_gsm", "bt", "bx_gsm", "by_gsm"])
        assert len(result[result["time_tag"] == "2026-01-01T00:00:00"]) == 1
        assert (
            result.loc[result["time_tag"] == "2026-01-01T00:00:00", "bz_gsm"].iloc[0]
            == 9.9
        )


class TestFormatColumnNames:
    def test_format_column_names_mag(self):
        df = pd.DataFrame(
            [
                {
                    "bx_gsm": 2.67,
                    "by_gsm": 1.9,
                    "bz_gsm": 1.61,
                }
            ]
        )
        result = format_column_names(
            df, columns={"bz_gsm": "bz", "bx_gsm": "bx", "by_gsm": "by"}
        )
        assert list(result.columns) == ["bx", "by", "bz"]

    def test_format_column_names_plasma(self):
        df = pd.DataFrame(
            [
                {
                    "proton_speed": 516,
                    "proton_temperature": 79712,
                    "proton_density": 3.34,
                }
            ]
        )
        result = format_column_names(
            df,
            columns={
                "proton_speed": "speed",
                "proton_temperature": "temperature",
                "proton_density": "density",
            },
        )
        assert list(result.columns) == ["speed", "temperature", "density"]


class TestDropExtraCols:
    def test_drop_extra_cols(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": True,
                    "source": "SOLAR1",
                    "bz_gsm": 1.5,
                }
            ]
        )
        result = drop_extra_cols(df)
        assert "active" not in result.columns
        assert "source" not in result.columns


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
        df = pd.DataFrame({"time_tag": ["2025-12-03T21:15:00.000"], "values": [324]})
        result = set_time_index(df)
        assert str(result.index.dtype) == "datetime64[ns]"


class TestCombineDataframes:
    def test_new_timestamps_appended(self):
        df_old = pd.DataFrame(
            {
                "time_tag": ["2026-01-01T00:00:00", "2026-01-01T00:01:00"],
                "bz_gsm": [1.5, 2.0],
            }
        )
        df_old = set_time_index(df_old)
        df_new = pd.DataFrame(
            {
                "time_tag": ["2026-01-01T00:02:00", "2026-01-01T00:03:00"],
                "bz_gsm": [3.0, 4.0],
            }
        )
        df_new = set_time_index(df_new)
        result = combine_dataframes(df_old, df_new)
        assert len(result) == 4

    def test_overlapping_timestamps_not_duplicated(self):
        df_old = pd.DataFrame(
            {
                "time_tag": ["2026-01-01T00:00:00", "2026-01-01T00:01:00"],
                "bz_gsm": [1.5, 2.0],
            }
        )
        df_old = set_time_index(df_old)
        df_new = pd.DataFrame(
            {
                "time_tag": ["2026-01-01T00:01:00", "2026-01-01T00:02:00"],
                "bz_gsm": [2.0, 3.0],
            }
        )
        df_new = set_time_index(df_new)
        result = combine_dataframes(df_old, df_new)
        assert len(result) == 3

    def test_result_is_sorted(self):
        df_old = pd.DataFrame({"time_tag": ["2026-01-01T00:02:00"], "bz_gsm": [3.0]})
        df_old = set_time_index(df_old)
        df_new = pd.DataFrame({"time_tag": ["2026-01-01T00:01:00"], "bz_gsm": [2.0]})
        df_new = set_time_index(df_new)
        result = combine_dataframes(df_old, df_new)
        assert result.index.is_monotonic_increasing


class TestMatchTimeIndex:
    def test_match_time_index(self):
        df1 = pd.DataFrame(
            {
                "time_tag": ["2025-05-03 21:15:00.000", "2025-10-03 21:15:00.000"],
                "values": [324, 56],
            }
        )
        df1 = set_time_index(df1)
        df2 = pd.DataFrame(
            {
                "time_tag": ["2025-08-03 21:15:00.000", "2025-12-03 21:15:00.000"],
                "values": [324, 56],
            }
        )
        df2 = set_time_index(df2)
        result1, result2 = match_time_index(df1, df2)
        assert result1.index.min() == result2.index.min()
        assert result2.index.max() == result2.index.max()


class TestJoinMagPlasma:
    def test_join_mag_plasma(self):
        df1 = pd.DataFrame(
            {
                "time_tag": ["2025-05-03 21:15:00.000", "2025-10-03 21:15:00.000"],
                "values1": [324, 56],
            }
        )
        df1 = set_time_index(df1)
        df2 = pd.DataFrame(
            {
                "time_tag": ["2025-05-03 21:15:00.000", "2025-10-03 21:15:00.000"],
                "values2": [324, 56],
            }
        )
        df2 = set_time_index(df2)
        result = join_mag_plasma(df1, df2)
        assert list(result.columns) == ["values2", "values1"]


class TestCastToFloat:
    def test_cast_to_float_string_data(self):
        df = pd.DataFrame({"speed": [str(1), str(2), str(3), str(4)]})
        result = cast_to_float(df)
        assert result["speed"].dtype == float

    def test_cast_to_float_integer_data(self):
        df = pd.DataFrame({"speed": [int(1), int(2), int(3), int(4)]})
        result = cast_to_float(df)
        assert result["speed"].dtype == float


class TestFilterInvalidData:
    def test_filter_invalid_data_replaces_negative_number_with_nan(self):
        df = pd.DataFrame(
            {
                "density": [10, 2.7, -3.4],
                "speed": [400.7, -50.2, 250.8],
                "temperature": [-100, 200000, 75000],
            }
        )
        result = filter_invalid_data(df)
        assert np.isnan(result.loc[2, "density"])
        assert np.isnan(result.loc[1, "speed"])
        assert np.isnan(result.loc[0, "temperature"])

    def test_filter_invalid_data_replaces_zero_with_nan(self):
        df = pd.DataFrame(
            {
                "density": [10, 2.7, 0],
                "speed": [400.7, -0, 250.8],
                "temperature": [0, 200000, 75000],
            }
        )
        result = filter_invalid_data(df)
        assert np.isnan(result.loc[2, "density"])
        assert np.isnan(result.loc[1, "speed"])
        assert np.isnan(result.loc[0, "temperature"])


class TestFilterOutliers:
    def test_97th_quantile_threshold(self):
        df = pd.DataFrame(
            {
                "bz_gsm": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 100.0],
            }
        )
        roc = df.diff().abs()
        threshold = roc.quantile(0.97)
        result = filter_outliers(df)
        above_threshold = roc > threshold
        below_threshold = roc <= threshold
        assert result["bz_gsm"][above_threshold["bz_gsm"]].isna().all()
        assert result["bz_gsm"][below_threshold["bz_gsm"]].notna().all()


class TestHandleMissingData:
    def test_handle_missing_data_interpolates_data(self):
        df = pd.DataFrame({"speed": [1, 2, 3, 4, None, None, 7, 8, 9, 10]})
        result = handle_missing_data(df)
        assert result["speed"].iloc[4] == 5 and result["speed"].iloc[5] == 6
        assert result.isnull().sum().sum() == 0

    def test_handle_missing_data_forward_fills_data(self):
        df = pd.DataFrame({"speed": [1, 2, 3, 4, 5, 6, 7, 8, None, None]})
        result = handle_missing_data(df)
        assert result.isnull().sum().sum() == 0

    def test_handle_missing_data_back_fills_data(self):
        df = pd.DataFrame({"speed": [None, None, 3, 4, 5, 6, 7, 8, 9, 10]})
        result = handle_missing_data(df)
        assert result.isnull().sum().sum() == 0


class TestAddPressureColumn:
    def test_add_pressure_column(self):
        df = pd.DataFrame({"density": [23], "speed": [5]})
        result = add_pressure_column(df)
        pressure = 23 * 5**2 * 1e21 * 1.6726e-27
        assert result["pressure"].iloc[0] == pressure


class TestRoundValues:
    def test_round_values(self):
        df = pd.DataFrame({"bz_gsm": [23.5678]})
        result = round_values(df)
        assert result["bz_gsm"].iloc[0] == 23.57


class TestSetIndexName:
    def test_set_index_name(self):
        df = pd.DataFrame({"values": [1, 2, 3]})
        result = set_index_name(df)
        assert result.index.name == "time"
