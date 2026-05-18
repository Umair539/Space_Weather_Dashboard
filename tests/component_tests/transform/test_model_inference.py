from src.transform.model_inference import model_inference
import pandas as pd
import numpy as np


class TestModelInference:
    def test_model_inference(self):
        index = pd.date_range("2026-01-01T00:00:00", periods=170, freq="h")
        model_inputs = pd.DataFrame(
            {
                "speed_mean": [0.0] * 170,
                "speed_std": [0.0] * 170,
                "temperature_mean": [0.0] * 170,
                "temperature_std": [0.0] * 170,
                "density_mean": [0.0] * 170,
                "density_std": [0.0] * 170,
                "bz_mean": [0.0] * 170,
                "bz_std": [0.0] * 170,
                "bx_mean": [0.0] * 170,
                "bx_std": [0.0] * 170,
                "by_mean": [0.0] * 170,
                "by_std": [0.0] * 170,
                "pressure_mean": [0.0] * 170,
                "pressure_std": [0.0] * 170,
                "predicted_ssn_mean": [0.0] * 170,
            },
            index=index,
        )
        model_inputs.index.name = "time"
        result = model_inference(model_inputs)
        assert list(result.columns) == ["dst_predictions"]
        assert str(result.index.dtype) == "datetime64[ns]"
        assert result["dst_predictions"].dtype == float
        assert len(result) == 3
