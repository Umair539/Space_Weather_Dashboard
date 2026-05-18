from src.transform.process_ssn import process_ssn
import pandas as pd


class TestProcessSsn:
    def test_process_ssn(self):
        df = pd.DataFrame(
            [
                {"Obsdate": "2026-01-01", "swpc_ssn": 45.0, "extra": 99},
                {"Obsdate": "2026-01-02", "swpc_ssn": 50.0, "extra": 99},
            ]
        )
        result = process_ssn(df)
        assert list(result.columns) == ["swpc_ssn"]
        assert str(result.index.dtype) == "datetime64[ns]"
        assert result.index.name == "time"
        assert result["swpc_ssn"].dtype == float

    def test_process_ssn_trims_to_12_years(self):
        df = pd.DataFrame(
            {
                "Obsdate": pd.date_range("2000-01-01", periods=5000, freq="D").strftime(
                    "%Y-%m-%d"
                ),
                "swpc_ssn": range(5000),
            }
        )
        result = process_ssn(df)
        assert len(result) == 4383
