from src.transform.process_rtsw import process_rtsw
import pandas as pd
import numpy as np


def make_mag(timestamps, active=True):
    return pd.DataFrame(
        [
            {
                "time_tag": t,
                "active": active,
                "bz_gsm": 1.5,
                "bx_gsm": 0.5,
                "by_gsm": 0.3,
                "bt": 2.0,
            }
            for t in timestamps
        ]
    )


def make_plasma(timestamps, active=True):
    return pd.DataFrame(
        [
            {
                "time_tag": t,
                "active": active,
                "proton_speed": 400.0,
                "proton_temperature": 50000.0,
                "proton_density": 3.0,
            }
            for t in timestamps
        ]
    )


class TestProcessRtsw:
    def test_output_columns(self):
        mag = make_mag(["2026-01-01T00:00:00", "2026-01-01T00:01:00"])
        plasma = make_plasma(["2026-01-01T00:00:00", "2026-01-01T00:01:00"])
        result = process_rtsw(mag, plasma, None, None)
        assert list(result.columns) == [
            "speed",
            "temperature",
            "density",
            "bz",
            "bx",
            "by",
            "bt",
            "pressure",
        ]

    def test_output_index(self):
        mag = make_mag(["2026-01-01T00:00:00", "2026-01-01T00:01:00"])
        plasma = make_plasma(["2026-01-01T00:00:00", "2026-01-01T00:01:00"])
        result = process_rtsw(mag, plasma, None, None)
        assert str(result.index.dtype) == "datetime64[ns]"
        assert result.index.name == "time"

    def test_output_dtypes_are_float(self):
        mag = make_mag(["2026-01-01T00:00:00", "2026-01-01T00:01:00"])
        plasma = make_plasma(["2026-01-01T00:00:00", "2026-01-01T00:01:00"])
        result = process_rtsw(mag, plasma, None, None)
        assert result.dtypes.eq(float).all()

    def test_old_data_combined(self):
        mag = make_mag(["2026-01-01T00:02:00"])
        plasma = make_plasma(["2026-01-01T00:02:00"])
        old_mag = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "bz_gsm": 1.0,
                    "bx_gsm": 0.4,
                    "by_gsm": 0.2,
                    "bt": 1.8,
                },
                {
                    "time_tag": "2026-01-01T00:01:00",
                    "bz_gsm": 1.2,
                    "bx_gsm": 0.5,
                    "by_gsm": 0.3,
                    "bt": 1.9,
                },
            ]
        )
        old_plasma = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "speed": 390.0,
                    "density": 2.5,
                    "temperature": 45000.0,
                },
                {
                    "time_tag": "2026-01-01T00:01:00",
                    "speed": 395.0,
                    "density": 2.8,
                    "temperature": 47000.0,
                },
            ]
        )
        result = process_rtsw(mag, plasma, old_mag, old_plasma)
        assert len(result) == 3
        assert pd.Timestamp("2026-01-01T00:00:00") in result.index
        assert pd.Timestamp("2026-01-01T00:01:00") in result.index
        assert pd.Timestamp("2026-01-01T00:02:00") in result.index

    def test_source_fallback_uses_inactive_when_active_all_nan(self):
        mag = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": True,
                    "bz_gsm": None,
                    "bx_gsm": None,
                    "by_gsm": None,
                    "bt": None,
                },
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": False,
                    "bz_gsm": 9.9,
                    "bx_gsm": 9.9,
                    "by_gsm": 9.9,
                    "bt": 9.9,
                },
            ]
        )
        plasma = make_plasma(["2026-01-01T00:00:00"])
        result = process_rtsw(mag, plasma, None, None)
        assert result["bz"].iloc[0] == 9.9

    def test_invalid_data_replaced(self):
        mag = make_mag(
            ["2026-01-01T00:00:00", "2026-01-01T00:01:00", "2026-01-01T00:02:00"]
        )
        plasma = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": True,
                    "proton_speed": -999.0,
                    "proton_temperature": 50000.0,
                    "proton_density": 3.0,
                },
                {
                    "time_tag": "2026-01-01T00:01:00",
                    "active": True,
                    "proton_speed": 400.0,
                    "proton_temperature": 50000.0,
                    "proton_density": 3.0,
                },
                {
                    "time_tag": "2026-01-01T00:02:00",
                    "active": True,
                    "proton_speed": 410.0,
                    "proton_temperature": 50000.0,
                    "proton_density": 3.0,
                },
            ]
        )
        result = process_rtsw(mag, plasma, None, None)
        assert result["speed"].isna().sum() == 0
        assert result["speed"].iloc[0] > 0

    def test_outliers_filtered(self):
        timestamps = [
            f"2026-01-01T{str(i // 60).zfill(2)}:{str(i % 60).zfill(2)}:00"
            for i in range(200)
        ]
        mag = make_mag(timestamps)
        plasma = pd.DataFrame(
            [
                {
                    "time_tag": t,
                    "active": True,
                    "proton_speed": 400.0 if i != 100 else 99999.0,
                    "proton_temperature": 50000.0,
                    "proton_density": 3.0,
                }
                for i, t in enumerate(timestamps)
            ]
        )
        result = process_rtsw(mag, plasma, None, None)
        spike_time = pd.Timestamp("2026-01-01T01:40:00")
        assert result.loc[spike_time, "speed"] < 99999.0
        assert result.loc[spike_time, "speed"] == 400.0

    def test_pressure_calculated(self):
        mag = make_mag(["2026-01-01T00:00:00"])
        plasma = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "active": True,
                    "proton_speed": 400.0,
                    "proton_temperature": 50000.0,
                    "proton_density": 5.0,
                }
            ]
        )
        result = process_rtsw(mag, plasma, None, None)
        expected = round(1.6726e-27 * 5.0 * 1e6 * (400.0**2) * 1e6 * 1e9, 2)
        assert result["pressure"].iloc[0] == expected

    def test_no_nulls_in_output(self):
        mag = make_mag(
            ["2026-01-01T00:00:00", "2026-01-01T00:01:00", "2026-01-01T00:02:00"]
        )
        plasma = make_plasma(
            ["2026-01-01T00:00:00", "2026-01-01T00:01:00", "2026-01-01T00:02:00"]
        )
        result = process_rtsw(mag, plasma, None, None)
        assert result.isna().sum().sum() == 0

    def test_values_rounded_to_2dp(self):
        mag = make_mag(["2026-01-01T00:00:00"])
        plasma = make_plasma(["2026-01-01T00:00:00"])
        result = process_rtsw(mag, plasma, None, None)
        for col in result.columns:
            assert result[col].iloc[0] == round(result[col].iloc[0], 2)
