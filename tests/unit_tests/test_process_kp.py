from src.transform.process_kp import filter_columns
import pandas as pd


class TestFilterColumns:
    def test_filter_columns(self):
        df = pd.DataFrame(
            {
                "time_tag": [1],
                "Kp": [23],
                "a_running": [34],
                "station_count": [78],
            }
        )
        result = filter_columns(df)
        assert list(result.columns) == ["time_tag", "Kp"]
