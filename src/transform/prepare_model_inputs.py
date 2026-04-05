import pandas as pd


def prepare_model_inputs(solar, smoothed_ssn):

    model_inputs = join_inputs(solar, smoothed_ssn)
    model_inputs = filter_and_reorder_inputs(model_inputs)
    model_inputs = normalise_data(model_inputs)
    model_inputs = downsample_data(model_inputs)

    return model_inputs.values


def join_inputs(solar, smoothed_ssn):
    model_inputs = pd.merge(solar, smoothed_ssn, "outer", "time")
    model_inputs["predicted_ssn"] = model_inputs["predicted_ssn"].ffill()
    model_inputs = model_inputs.dropna()
    return model_inputs


def filter_and_reorder_inputs(model_inputs):
    features = [
        "speed",
        "temperature",
        "density",
        "bz",
        "bx",
        "by",
        "pressure",
        "predicted_ssn",
    ]
    model_inputs = model_inputs[features]
    return model_inputs


def normalise_data(model_inputs):
    stats = {
        "median": (410.43, 76430.0, 3.19466, -0.01, -0.6, -0.02, 573059.4476, 57.9),
        "iqr": (128.55, 107250.0, 3.8, 3.72, 5.39, 4.98, 695837.1271, 86.3),
    }

    model_inputs = (model_inputs - stats["median"]) / stats["iqr"]
    return model_inputs


def downsample_data(model_inputs):
    model_inputs = model_inputs.resample("h").agg(["mean", "std"])
    model_inputs.columns = ["_".join(col) for col in model_inputs]
    model_inputs.drop("predicted_ssn_std", axis=1, inplace=True)
    return model_inputs
