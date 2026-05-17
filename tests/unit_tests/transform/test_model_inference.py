from src.transform.model_inference import (
    prepare_dataset,
    perform_inference,
    denormalise_predictions,
    prediction_dataframe,
)

import numpy as np
import pandas as pd
from unittest.mock import MagicMock


class TestPrepareDataset:
    def test_output_shape_correct(self):
        inputs = np.random.rand(200, 16).astype(np.float32)
        result = prepare_dataset(inputs, sequence_length=168)
        assert result.shape == (33, 168, 16)

    def test_sequence_length_respected(self):
        inputs = np.random.rand(170, 16).astype(np.float32)
        result = prepare_dataset(inputs, sequence_length=168)
        assert result.shape[0] == 3

    def test_dtype_is_float32(self):
        inputs = np.random.rand(200, 16).astype(np.float64)
        result = prepare_dataset(inputs, sequence_length=168)
        assert result.dtype == np.float32


class TestPerformInference:
    def test_returns_flattened_predictions(self):
        mock_sess = MagicMock()
        mock_sess.run.return_value = [np.array([[1.0], [2.0], [3.0]])]
        X = np.random.rand(3, 168, 16).astype(np.float32)
        result = perform_inference(X, mock_sess)
        assert result.shape == (3,)

    def test_correct_input_key_used(self):
        mock_sess = MagicMock()
        mock_sess.run.return_value = [np.array([[1.0]])]
        X = np.random.rand(1, 168, 16).astype(np.float32)
        perform_inference(X, mock_sess)
        call_args = mock_sess.run.call_args
        assert "input_layer:0" in call_args[0][1]


class TestDenormalisePredictions:
    def test_denormalise_zero_gives_median(self):
        result = denormalise_predictions(np.array([0.0]))
        assert result[0] == -8.0

    def test_denormalise_one_gives_median_plus_iqr(self):
        result = denormalise_predictions(np.array([1.0]))
        assert result[0] == 11.0

    def test_denormalise_negative_one(self):
        result = denormalise_predictions(np.array([-1.0]))
        assert result[0] == -27.0


class TestPredictionDataframe:
    def test_index_offset_by_one_hour(self):
        index = pd.date_range("2026-01-01", periods=170, freq="h")
        model_inputs = pd.DataFrame({"col": range(170)}, index=index)
        predictions = np.ones(3)
        result = prediction_dataframe(predictions, model_inputs, sequence_length=168)
        assert result.index[0] == pd.Timestamp("2026-01-08 00:00:00")

    def test_output_column_named_correctly(self):
        index = pd.date_range("2026-01-01", periods=170, freq="h")
        model_inputs = pd.DataFrame({"col": range(170)}, index=index)
        predictions = np.ones(3)
        result = prediction_dataframe(predictions, model_inputs, sequence_length=168)
        assert list(result.columns) == ["dst_predictions"]

    def test_length_matches_predictions(self):
        index = pd.date_range("2026-01-01", periods=170, freq="h")
        model_inputs = pd.DataFrame({"col": range(170)}, index=index)
        predictions = np.ones(3)
        result = prediction_dataframe(predictions, model_inputs, sequence_length=168)
        assert len(result) == 3
