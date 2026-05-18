from src.transform.prepare_model_inputs import prepare_model_inputs
import pandas as pd


class TestPrepareModelInputs:
    def test_prepare_model_inputs(self):
        index = pd.date_range("2026-01-01T00:00:00", periods=60, freq="min")
        solar = pd.DataFrame(
            {
                "speed": [400.0] * 60,
                "temperature": [50000.0] * 60,
                "density": [3.0] * 60,
                "bz": [-1.0] * 60,
                "bx": [0.5] * 60,
                "by": [0.3] * 60,
                "pressure": [500000.0] * 60,
            },
            index=index,
        )
        solar.index.name = "time"
        smoothed_ssn = pd.DataFrame(
            {"predicted_ssn": [57.9]},
            index=pd.to_datetime(["2026-01-01T00:00:00"]),
        )
        smoothed_ssn.index.name = "time"
        result = prepare_model_inputs(solar, smoothed_ssn)
        assert result.index.freq == pd.tseries.frequencies.to_offset("h")
        assert "predicted_ssn_std" not in result.columns
        assert all("_mean" in col or "_std" in col for col in result.columns)
        assert len(result) == 1

    def test_prepare_model_inputs_normalised(self):
        index = pd.date_range("2026-01-01T00:00:00", periods=60, freq="min")
        solar = pd.DataFrame(
            {
                "speed": [410.43] * 60,
                "temperature": [76430.0] * 60,
                "density": [3.19466] * 60,
                "bz": [-0.01] * 60,
                "bx": [-0.6] * 60,
                "by": [-0.02] * 60,
                "pressure": [573059.4476] * 60,
            },
            index=index,
        )
        solar.index.name = "time"
        smoothed_ssn = pd.DataFrame(
            {"predicted_ssn": [57.9]},
            index=pd.to_datetime(["2026-01-01T00:00:00"]),
        )
        smoothed_ssn.index.name = "time"
        result = prepare_model_inputs(solar, smoothed_ssn)
        mean_cols = [col for col in result.columns if "_mean" in col]
        assert (result[mean_cols].iloc[0] == 0.0).all()
