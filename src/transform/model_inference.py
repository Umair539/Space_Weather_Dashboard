from keras import utils, models
import pandas as pd

dst_model = models.load_model("model/model.keras")


def model_inference(model_inputs, dst, model=dst_model):
    model_inputs = prepare_dataset(model_inputs)
    predictions = run_inference(model_inputs, model)
    predictions = denormalise_predictions(predictions)
    dst = align_predictions(predictions, dst)

    return dst


def prepare_dataset(model_inputs):
    model_inputs = utils.timeseries_dataset_from_array(
        data=model_inputs,
        targets=None,
        sequence_length=168,
        sampling_rate=1,
        sequence_stride=1,
        shuffle=False,
    )
    return model_inputs


def run_inference(model_inputs, model):
    predictions = model.predict(model_inputs).flatten()
    return predictions


def denormalise_predictions(predictions):
    stats = (-8, 19)
    predictions = (predictions * stats[1]) + stats[0]
    return predictions


def align_predictions(predictions, dst):
    dst = dst[-len(predictions) :].copy()
    dst["predictions"] = predictions
    next_hour = dst.index[-1] + pd.Timedelta(hours=1)
    dst.loc[next_hour, :] = None
    dst["predictions"] = dst["predictions"].shift(1)
    return dst
