from src.transform.process_kp import process_kp
import pandas as pd


class TestProcessKp:
    def test_process_kp(self):
        df = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "Kp": 2.3,
                    "a_running": 34,
                    "station_count": 78,
                },
                {
                    "time_tag": "2026-01-01T03:00:00",
                    "Kp": 3.1,
                    "a_running": 12,
                    "station_count": 65,
                },
            ]
        )
        result = process_kp(df)
        assert list(result.columns) == ["Kp"]
        assert str(result.index.dtype) == "datetime64[ns]"
        assert result.index.name == "time"
        assert result["Kp"].dtype == float
