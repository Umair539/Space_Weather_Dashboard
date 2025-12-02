import requests
import logging
import pandas as pd
from src.utils.logging_utils import setup_logger

# Configure the logger
logger = setup_logger(__name__, "extract_data.log", level=logging.DEBUG)

def extract_data_from_json(url):
    try:
        #Fetch JSON data from NOAA and convert to DataFrame
        response = get_response(url)
        json_data = extract_json(response)
        df = convert_to_df(json_data)
        return df
    
    except Exception as e:
        logger.error(f'Error fetching json data from {url}: {e}')
    
def get_response(url):
    return requests.get(url, timeout=10)

def extract_json(response):
    return response.json()

def convert_to_df(json_data):
    return pd.DataFrame(json_data[1:], columns=json_data[0])