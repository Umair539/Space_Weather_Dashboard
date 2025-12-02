import pandas as pd
from src.transform.process_solar_wind import process_solar_wind
from src.transform.aggregate_solar_wind import aggregate_solar_wind
from src.transform.process_dst import process_dst
from src.transform.process_kp import process_kp
from src.utils.logging_utils import setup_logger

logger = setup_logger("transform_data", "transform_data.log")

def transform_data(extracted_data):
    try:
        mag, plasma, dst, kp = extracted_data
        solar = process_solar_wind(mag, plasma)
        solar_agg = aggregate_solar_wind(solar)
        dst = process_dst(dst)
        kp = process_kp(kp)
        
        return (solar, solar_agg, dst, kp)
    except Exception as e:
        logger.error(f"Data transformation failed: {str(e)}")