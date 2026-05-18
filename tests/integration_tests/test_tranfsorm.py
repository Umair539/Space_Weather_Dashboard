import pickle
from src.transform.transform import transform_data


class TestTransformDataIntegration:
    def test_transform_data(self):
        with open("tests/fixtures/saved_data.pkl", "rb") as f:
            saved_data = pickle.load(f)

        solar, dst, kp, ssn, dst_predictions = transform_data(saved_data)

        assert len(solar) > 0
        assert len(dst) > 0
        assert len(kp) > 0
        assert len(ssn) > 0
        assert len(dst_predictions) > 0

        assert list(solar.columns) == [
            "density",
            "speed",
            "temperature",
            "bz",
            "bx",
            "by",
            "bt",
            "pressure",
        ]
        assert list(dst.columns) == ["dst"]
        assert list(kp.columns) == ["Kp"]
        assert list(ssn.columns) == ["swpc_ssn"]
        assert list(dst_predictions.columns) == ["dst_predictions"]

        assert solar.index.name == "time"
        assert dst.index.name == "time"
        assert kp.index.name == "time"
        assert ssn.index.name == "time"
        assert dst_predictions.index.name == "time"

        assert solar.isna().sum().sum() == 0
        assert dst.isna().sum().sum() == 0
        assert kp.isna().sum().sum() == 0
        assert ssn.isna().sum().sum() == 0
        assert dst_predictions.isna().sum().sum() == 0
