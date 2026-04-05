from keras import utils, models
import pandas as pd


def model_inference(model_inputs, dst):
    model_inputs = utils.timeseries_dataset_from_array(
        data=model_inputs,
        targets=None,
        sequence_length=168,
        sampling_rate=1,
        sequence_stride=1,
        shuffle=False,
    )

    model = models.load_model("model/model.keras")
    predictions = model.predict(model_inputs).flatten()

    stats = (-8, 19)
    predictions = (predictions * stats[1]) + stats[0]

    dst = dst[-len(predictions) :].copy()
    dst["predictions"] = predictions
    next_hour = dst.index[-1] + pd.Timedelta(hours=1)
    dst.loc[next_hour, :] = None
    dst["predictions"] = dst["predictions"].shift(1)

    return dst
