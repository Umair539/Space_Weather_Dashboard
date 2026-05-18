from src.transform.process_dst import process_dst
import pandas as pd


class TestProcessDst:
    def test_process_dst(self):
        df = pd.DataFrame(
            [
                {"time_tag": "2026-01-01T00:00:00", "dst": -25.0, "extra": 99},
                {"time_tag": "2026-01-01T01:00:00", "dst": -30.0, "extra": 99},
            ]
        )
        result = process_dst(df)
        assert list(result.columns) == ["dst"]
        assert str(result.index.dtype) == "datetime64[ns]"
        assert result.index.name == "time"
        assert result["dst"].dtype == float
