from src.transform.prepare_model_inputs import (
    join_inputs,
    filter_and_reorder_inputs,
    normalise_data,
    filter_complete_hours,
    downsample_data,
)

import pandas as pd
import numpy as np


class TestJoinInputs:
    def test_monthly_ssn_forward_fills_across_month_boundary(self):
        solar = pd.DataFrame(
            {
                "speed": [400.0, 410.0, 420.0, 430.0],
                "temperature": [50000.0, 60000.0, 70000.0, 80000.0],
                "density": [3.0, 4.0, 5.0, 6.0],
                "bz": [-1.0, 1.0, -2.0, 2.0],
                "bx": [0.5, 0.6, 0.7, 0.8],
                "by": [0.3, 0.4, 0.5, 0.6],
                "pressure": [500000.0, 600000.0, 700000.0, 800000.0],
            },
            index=pd.to_datetime(
                [
                    "2026-04-29T00:00:00",
                    "2026-04-30T00:00:00",
                    "2026-05-01T00:00:00",
                    "2026-05-02T00:00:00",
                ]
            ),
        )
        solar.index.name = "time"
        smoothed_ssn = pd.DataFrame(
            {"predicted_ssn": [57.9, 58.5]},
            index=pd.to_datetime(["2026-04-01T00:00:00", "2026-05-01T00:00:00"]),
        )
        smoothed_ssn.index.name = "time"
        result = join_inputs(solar, smoothed_ssn)
        assert result.loc[pd.Timestamp("2026-04-29T00:00:00"), "predicted_ssn"] == 57.9
        assert result.loc[pd.Timestamp("2026-04-30T00:00:00"), "predicted_ssn"] == 57.9
        assert result.loc[pd.Timestamp("2026-05-01T00:00:00"), "predicted_ssn"] == 58.5
        assert result.loc[pd.Timestamp("2026-05-02T00:00:00"), "predicted_ssn"] == 58.5

    def test_predicted_ssn_forward_filled(self):
        solar = pd.DataFrame(
            {
                "speed": [400.0, 410.0],
                "temperature": [50000.0, 60000.0],
                "density": [3.0, 4.0],
                "bz": [-1.0, 1.0],
                "bx": [0.5, 0.6],
                "by": [0.3, 0.4],
                "pressure": [500000.0, 600000.0],
            },
            index=pd.to_datetime(["2026-01-01T00:00:00", "2026-01-01T00:01:00"]),
        )
        solar.index.name = "time"
        smoothed_ssn = pd.DataFrame(
            {"predicted_ssn": [57.9]},
            index=pd.to_datetime(["2026-01-01T00:00:00"]),
        )
        smoothed_ssn.index.name = "time"
        result = join_inputs(solar, smoothed_ssn)
        assert result["predicted_ssn"].isna().sum() == 0
        assert result["predicted_ssn"].iloc[1] == 57.9

    def test_nan_rows_dropped(self):
        solar = pd.DataFrame(
            {
                "speed": [400.0, None],
                "temperature": [50000.0, None],
                "density": [3.0, None],
                "bz": [-1.0, None],
                "bx": [0.5, None],
                "by": [0.3, None],
                "pressure": [500000.0, None],
            },
            index=pd.to_datetime(["2026-01-01T00:00:00", "2026-01-01T00:01:00"]),
        )
        solar.index.name = "time"
        smoothed_ssn = pd.DataFrame(
            {"predicted_ssn": [57.9]},
            index=pd.to_datetime(["2026-01-01T00:00:00"]),
        )
        smoothed_ssn.index.name = "time"
        result = join_inputs(solar, smoothed_ssn)
        assert result.isna().sum().sum() == 0


class TestFilterAndReorderInputs:
    def test_only_feature_columns_remain(self):
        df = pd.DataFrame(
            [
                {
                    "speed": 400.0,
                    "temperature": 50000.0,
                    "density": 3.0,
                    "bz": -1.0,
                    "bx": 0.5,
                    "by": 0.3,
                    "pressure": 500000.0,
                    "predicted_ssn": 57.9,
                    "extra_col": 99,
                }
            ]
        )
        result = filter_and_reorder_inputs(df)
        assert list(result.columns) == [
            "speed",
            "temperature",
            "density",
            "bz",
            "bx",
            "by",
            "pressure",
            "predicted_ssn",
        ]

    def test_column_order_correct(self):
        df = pd.DataFrame(
            [
                {
                    "predicted_ssn": 57.9,
                    "pressure": 500000.0,
                    "by": 0.3,
                    "bx": 0.5,
                    "bz": -1.0,
                    "density": 3.0,
                    "temperature": 50000.0,
                    "speed": 400.0,
                }
            ]
        )
        result = filter_and_reorder_inputs(df)
        assert list(result.columns) == [
            "speed",
            "temperature",
            "density",
            "bz",
            "bx",
            "by",
            "pressure",
            "predicted_ssn",
        ]


class TestNormaliseData:
    def test_normalised_values_correct(self):
        df = pd.DataFrame(
            [
                {
                    "speed": 410.43,
                    "temperature": 76430.0,
                    "density": 3.19466,
                    "bz": -0.01,
                    "bx": -0.6,
                    "by": -0.02,
                    "pressure": 573059.4476,
                    "predicted_ssn": 57.9,
                }
            ]
        )
        result = normalise_data(df)
        assert (result.iloc[0] == 0.0).all()

    def test_normalised_shape_unchanged(self):
        df = pd.DataFrame(
            [
                {
                    "speed": 400.0,
                    "temperature": 50000.0,
                    "density": 3.0,
                    "bz": -1.0,
                    "bx": 0.5,
                    "by": 0.3,
                    "pressure": 500000.0,
                    "predicted_ssn": 57.9,
                }
            ]
        )
        result = normalise_data(df)
        assert result.shape == df.shape


class TestFilterCompleteHours:
    def test_complete_hour_kept(self):
        index = pd.date_range("2026-01-01T00:00:00", periods=60, freq="min")
        df = pd.DataFrame({"speed": [400.0] * 60}, index=index)
        result = filter_complete_hours(df)
        assert len(result) == 60

    def test_incomplete_hour_dropped(self):
        index = pd.date_range("2026-01-01T00:00:00", periods=59, freq="min")
        df = pd.DataFrame({"speed": [400.0] * 59}, index=index)
        result = filter_complete_hours(df)
        assert len(result) == 0


class TestDownsampleData:
    def test_output_index_is_hourly(self):
        index = pd.date_range("2026-01-01T00:00:00", periods=60, freq="min")
        df = pd.DataFrame(
            {
                "speed": [400.0] * 60,
                "temperature": [50000.0] * 60,
                "density": [3.0] * 60,
                "bz": [-1.0] * 60,
                "bx": [0.5] * 60,
                "by": [0.3] * 60,
                "pressure": [500000.0] * 60,
                "predicted_ssn": [57.9] * 60,
            },
            index=index,
        )
        result = downsample_data(df)
        assert len(result) == 1

    def test_predicted_ssn_std_dropped(self):
        index = pd.date_range("2026-01-01T00:00:00", periods=60, freq="min")
        df = pd.DataFrame(
            {
                "speed": [400.0] * 60,
                "temperature": [50000.0] * 60,
                "density": [3.0] * 60,
                "bz": [-1.0] * 60,
                "bx": [0.5] * 60,
                "by": [0.3] * 60,
                "pressure": [500000.0] * 60,
                "predicted_ssn": [57.9] * 60,
            },
            index=index,
        )
        result = downsample_data(df)
        assert "predicted_ssn_std" not in result.columns

    def test_columns_are_mean_std_suffixed(self):
        index = pd.date_range("2026-01-01T00:00:00", periods=60, freq="min")
        df = pd.DataFrame(
            {
                "speed": [400.0] * 60,
                "temperature": [50000.0] * 60,
                "density": [3.0] * 60,
                "bz": [-1.0] * 60,
                "bx": [0.5] * 60,
                "by": [0.3] * 60,
                "pressure": [500000.0] * 60,
                "predicted_ssn": [57.9] * 60,
            },
            index=index,
        )
        result = downsample_data(df)
        assert all("_mean" in col or "_std" in col for col in result.columns)
