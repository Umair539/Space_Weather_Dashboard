from src.transform.process_old_solar_wind import process_old_solar_wind
import pandas as pd


class TestProcessOldSolarWind:
    def test_process_old_solar_wind(self):
        mag = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "bz_gsm": 1.5,
                    "bx_gsm": 0.5,
                    "by_gsm": 0.3,
                    "bt": 2.0,
                    "extra": 99,
                },
                {
                    "time_tag": "2026-01-01T00:01:00",
                    "bz_gsm": 2.0,
                    "bx_gsm": 0.6,
                    "by_gsm": 0.4,
                    "bt": 2.5,
                    "extra": 99,
                },
            ]
        )
        plasma = pd.DataFrame(
            [
                {
                    "time_tag": "2026-01-01T00:00:00",
                    "speed": 400.0,
                    "density": 3.0,
                    "temperature": 50000.0,
                },
                {
                    "time_tag": "2026-01-01T00:01:00",
                    "speed": 410.0,
                    "density": 4.0,
                    "temperature": 60000.0,
                },
            ]
        )
        result_mag, result_plasma = process_old_solar_wind(mag, plasma)
        assert list(result_mag.columns) == ["bz", "bx", "by", "bt"]
        assert list(result_plasma.columns) == ["speed", "density", "temperature"]
        assert str(result_mag.index.dtype) == "datetime64[ns]"
        assert str(result_plasma.index.dtype) == "datetime64[ns]"
