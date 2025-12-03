from src.transform.process_solar_wind import cast_to_float
from src.transform.process_solar_wind import handle_missing_data
from src.transform.process_solar_wind import set_index_name
import pandas as pd


class TestCastToFloat:
    def test_cast_to_float_string_data(self):
        df = pd.DataFrame({"speed": [str(1), str(2), str(3), str(4)]})
        result = cast_to_float(df)
        assert result["speed"].dtype == float

    def test_cast_to_float_integer_data(self):
        df = pd.DataFrame({"speed": [int(1), int(2), int(3), int(4)]})
        result = cast_to_float(df)
        assert result["speed"].dtype == float

    pass


class TestInterpolateMissingData:
    def test_handle_missing_data_interpolates_data(self):
        df = pd.DataFrame(
            {
                "speed": [1, 2, 3, 4, None, None, 7, 8, 9, 10],
            }
        )
        result = handle_missing_data(df)
        assert result.isnull().sum().sum() == 0

    def test_handle_missing_data_forward_fills_data(self):
        df = pd.DataFrame({"speed": [1, 2, 3, 4, 5, 6, 7, 8, None, None]})
        result = handle_missing_data(df)
        assert result.isnull().sum().sum() == 0

    def test_handle_missing_data_back_fills_data(self):
        df = pd.DataFrame({"speed": [None, None, 3, 4, 5, 6, 7, 8, 9, 10]})
        result = handle_missing_data(df)
        assert result.isnull().sum().sum() == 0

    pass


class TestSetIndexName:
    def test_set_index_name(self):
        df = pd.DataFrame(
            {"time": [1, 2, 3, 4, 5], "values": [324, 3566, 8776, 213, 9876]}
        )
        result = set_index_name(df)
        assert result.index.name == "time"

    pass
