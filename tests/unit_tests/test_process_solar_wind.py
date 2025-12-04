from src.transform.process_solar_wind import cast_to_float
from src.transform.process_solar_wind import handle_missing_data
from src.transform.process_solar_wind import set_index_name
from src.transform.process_solar_wind import set_time_index
from src.transform.process_solar_wind import filter_columns
from src.transform.process_solar_wind import format_column_name
from src.transform.process_solar_wind import add_pressure_column
from src.transform.process_solar_wind import match_time_index
from src.transform.process_solar_wind import join_mag_plasma
from src.transform.process_solar_wind import round_values

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


class TestInterpolateMissingData:
    def test_handle_missing_data_interpolates_data(self):
        df = pd.DataFrame(
            {
                "speed": [1, 2, 3, 4, None, None, 7, 8, 9, 10],
            }
        )
        result = handle_missing_data(df)
        assert result["speed"].iloc[4] == 5 and result["speed"].iloc[5] == 6
        assert result.isnull().sum().sum() == 0

    def test_handle_missing_data_forward_fills_data(self):
        df = pd.DataFrame({"speed": [1, 2, 3, 4, 5, 6, 7, 8, None, None]})
        result = handle_missing_data(df)
        assert result.isnull().sum().sum() == 0

    def test_handle_missing_data_back_fills_data(self):
        df = pd.DataFrame({"speed": [None, None, 3, 4, 5, 6, 7, 8, 9, 10]})
        result = handle_missing_data(df)
        assert result.isnull().sum().sum() == 0


class TestSetTimeIndex:
    def test_set_time_index(self):
        df = pd.DataFrame({"time_tag": ["2025-12-03 21:15:00.000"], "values": [324]})
        result = set_time_index(df)
        assert str(result.index.dtype) == "datetime64[ns]"


class TestSetIndexName:
    def test_set_index_name(self):
        df = pd.DataFrame(
            {"time": [1, 2, 3, 4, 5], "values": [324, 3566, 8776, 213, 9876]}
        )
        result = set_index_name(df)
        assert result.index.name == "time"


class TestFilterColumns:
    def test_filter_columns(self):
        df = pd.DataFrame(
            {
                "time_tag": [1],
                "bz_gsm": [23],
                "bt": [34],
                "bx_gsm": [78],
                "by_gsm": [5432],
            }
        )
        result = filter_columns(df)
        assert list(result.columns) == ["time_tag", "bz_gsm", "bt"]


class TestFormatColumnName:
    def test_format_column_name(self):
        df = pd.DataFrame(
            {
                "bz_gsm": [23],
            }
        )
        result = format_column_name(df)
        assert list(result.columns) == ["bz"]


class TestAddPressureColumn:
    def test_add_pressure_column(self):
        df = pd.DataFrame(
            {
                "density": [23],
                "speed": [5],
            }
        )
        result = add_pressure_column(df)
        pressure = 23 * 5**2 * 1e21 * 1.6726e-27
        assert result["pressure"].iloc[0] == pressure


class TestMatchTimeIndex:
    def test_match_time_index(self):
        df1 = pd.DataFrame(
            {
                "time_tag": ["2025-05-03 21:15:00.000", "2025-10-03 21:15:00.000"],
                "values": [324, 56],
            }
        )
        df1 = set_time_index(df1)
        df2 = pd.DataFrame(
            {
                "time_tag": ["2025-08-03 21:15:00.000", "2025-12-03 21:15:00.000"],
                "values": [324, 56],
            }
        )
        df2 = set_time_index(df2)
        result1, result2 = match_time_index(df1, df2)
        print(result1.index.dtype)

        assert result1.index.min() == result2.index.min()
        assert result2.index.max() == result2.index.max()


class TestRoundValues:
    def test_round_values(self):
        df = pd.DataFrame(
            {
                "bz_gsm": [23.5678],
            }
        )
        result = round_values(df)
        assert result["bz_gsm"].iloc[0] == 23.57


class TestJoinMagPlasma:
    def test_join_mag_plasma(self):
        df1 = pd.DataFrame(
            {
                "time_tag": ["2025-05-03 21:15:00.000", "2025-10-03 21:15:00.000"],
                "values1": [324, 56],
            }
        )
        df1 = set_time_index(df1)
        df2 = pd.DataFrame(
            {
                "time_tag": ["2025-05-03 21:15:00.000", "2025-10-03 21:15:00.000"],
                "values2": [324, 56],
            }
        )
        df2 = set_time_index(df2)
        result = join_mag_plasma(df1, df2)
        assert list(result.columns) == ["values2", "values1"]
