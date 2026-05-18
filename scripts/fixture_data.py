from dotenv import load_dotenv

load_dotenv(".env.dev")

import pickle
from src.extract.extract import extract_saved_data

print("Pulling saved data from R2...")
saved_data = extract_saved_data(filter_raw=False)

import os

os.makedirs("tests/fixtures", exist_ok=True)

with open("tests/fixtures/saved_data.pkl", "wb") as f:
    pickle.dump(saved_data, f)

print("Fixture saved to tests/fixtures/saved_data.pkl")
