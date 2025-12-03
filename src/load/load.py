from src.utils.logging_utils import setup_logger

logger = setup_logger("load_data", "load_data.log")


def load_raw_data(extracted_data):
    try:
        mag, plasma, dst, kp = extracted_data

        logger.info("Saving raw data...")

        mag.to_csv("data/raw/mag.csv", index=False)
        plasma.to_csv("data/raw/plasma.csv", index=False)
        dst.to_csv("data/raw/dst.csv", index=False)
        kp.to_csv("data/raw/kp.csv", index=False)

        logger.info("Raw data saved.")
        return
    except Exception as e:
        logger.error(f"Failed to load raw data: {str(e)}")


def load_transformed_data(transformed_data):
    try:
        solar, solar_agg, dst, kp = transformed_data

        logger.info("Saving transformed data...")

        solar.to_csv("data/transformed/solar.csv", index=True)
        solar_agg.to_csv("data/transformed/solar_agg.csv", index=True)
        dst.to_csv("data/transformed/dst.csv", index=True)
        kp.to_csv("data/transformed/kp.csv", index=True)

        logger.info("Transformed data saved.")
        return
    except Exception as e:
        logger.error(f"Failed to load transformed data: {str(e)}")
