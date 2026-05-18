from src.transform.process_smoothed_ssn import process_smoothed_ssn
import pandas as pd


class TestProcessSmoothedSsn:
    def test_process_smoothed_ssn(self):
        df = pd.DataFrame(
            [
                {"time-tag": "2026-01-01", "predicted_ssn": 57.9, "extra": 99},
                {"time-tag": "2026-02-01", "predicted_ssn": 58.5, "extra": 99},
            ]
        )
        result = process_smoothed_ssn(df)
        assert list(result.columns) == ["predicted_ssn"]
        assert str(result.index.dtype) == "datetime64[ns]"
        assert result.index.name == "time"
        assert result["predicted_ssn"].dtype == float
