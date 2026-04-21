import onnxruntime as rt
import numpy as np
import pandas as pd
from src.transform.process_rtsw import round_values

sess = rt.InferenceSession("model/model.onnx")


def model_inference(model_inputs):
    X = model_inputs
    X = prepare_dataset(model_inputs.values)
    predictions = perform_inference(X, sess)
    predictions = denormalise_predictions(predictions)
    predictions = prediction_dataframe(predictions, model_inputs)
    predictions = round_values(predictions)
    return predictions


def prepare_dataset(model_inputs, sequence_length=168):
    model_inputs = np.asarray(model_inputs, dtype=np.float32)
    n = len(model_inputs) - sequence_length + 1
    X = np.empty((n, sequence_length, model_inputs.shape[1]), dtype=np.float32)
    for i in range(n):
        X[i] = model_inputs[i : i + sequence_length]
    return X


def perform_inference(X, sess):
    predictions = sess.run(None, {"input_layer:0": X})[0].flatten()
    return predictions


def denormalise_predictions(predictions):
    stats = (-8, 19)
    return (predictions * stats[1]) + stats[0]


def prediction_dataframe(predictions, model_inputs, sequence_length=168):
    prediction_times = model_inputs.index[sequence_length - 1 :] + pd.Timedelta(hours=1)
    return pd.DataFrame({"dst_predictions": predictions}, index=prediction_times)
