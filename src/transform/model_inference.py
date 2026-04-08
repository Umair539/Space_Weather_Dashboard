import onnxruntime as rt
import numpy as np
import pandas as pd

sess = rt.InferenceSession("model/model.onnx")


def model_inference(model_inputs, dst):
    X = prepare_dataset(model_inputs)
    predictions = sess.run(None, {"input_layer:0": X})[0].flatten()
    predictions = denormalise_predictions(predictions)
    dst = align_predictions(predictions, dst)
    return dst


def prepare_dataset(model_inputs, sequence_length=168):
    X = np.array(
        [
            model_inputs[i : i + sequence_length]
            for i in range(len(model_inputs) - sequence_length + 1)
        ]
    )
    return X.astype(np.float32)


def denormalise_predictions(predictions):
    stats = (-8, 19)
    return (predictions * stats[1]) + stats[0]


def align_predictions(predictions, dst):
    dst = dst[-len(predictions) :].copy()
    dst["predictions"] = predictions
    next_hour = dst.index[-1] + pd.Timedelta(hours=1)
    dst.loc[next_hour, :] = None
    dst["predictions"] = dst["predictions"].shift(1)
    return dst
