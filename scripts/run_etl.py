from src.extract.extract import extract_data
from src.transform.transform import transform_data
from src.load.load import load_raw_data
from src.load.load import load_transformed_data
from src.utils.logging_utils import setup_logger
import time

def main():
    # Setup ETL pipeline logger   
    logger = setup_logger("etl_pipeline", "etl_pipeline.log")
    while True:
        print('Attempting ETL')
        try:
            extracted_data = extract_data()

            load_raw_data(extracted_data)

            transformed_data = transform_data(extracted_data)

            load_transformed_data(transformed_data)
            del extracted_data
            del transformed_data
            print('ETL successful')
            
        except Exception as e:
            logger.error(f"ETL pipeline failed: {e}")
            print('ETL unsuccessful')
            
        print('Sleeping for 60 seconds')
        time.sleep(60)

if __name__ == "__main__":
    main()
