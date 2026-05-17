from src.transform.process_ssn import filter_ssn
import pandas as pd


class TestFilterSsn:
    def test_returns_last_4383_rows(self):
        df = pd.DataFrame({"ssn": range(5000)})
        result = filter_ssn(df)
        assert len(result) == 4383

    def test_returns_all_rows_when_less_than_4383(self):
        df = pd.DataFrame({"ssn": range(100)})
        result = filter_ssn(df)
        assert len(result) == 100

    def test_returns_correct_tail(self):
        df = pd.DataFrame({"ssn": range(5000)})
        result = filter_ssn(df)
        assert result["ssn"].iloc[0] == 617
        assert result["ssn"].iloc[-1] == 4999
