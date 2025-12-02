import pandas as pd
from src.utils.logging_utils import setup_logger

logger = setup_logger("load_data", "load_data.log")

def load_raw_data(extracted_data):
    try:
        mag, plasma = extracted_data
        mag.to_csv('data/raw/mag.csv', index=False)
        plasma.to_csv('data/raw/plasma.csv', index=False)
        return
    except Exception as e:
        logger.error(f'Failed to load raw data: {str(e)}')

def load_transformed_data(transformed_data):
    try:
        solar, solar_agg = transformed_data
        solar = solar.rename_axis('time')
        solar.to_csv('data/transformed/solar.csv', index=True)
        solar_agg = solar_agg.rename_axis('time')
        solar_agg.to_csv('data/transformed/solar_agg.csv', index=True)
        return
    except Exception as e:
        logger.error(f'Failed to load transformed data: {str(e)}')