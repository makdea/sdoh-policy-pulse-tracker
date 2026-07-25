import os
from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT = os.environ.get("GCP_PROJECT", "")
GCP_KEYFILE_PATH = os.environ.get("GCP_KEYFILE_PATH", "")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "US")
CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "")
RAW_DIR = "data/raw"

SAHIE_YEARS = list(range(2016, 2023))   # 2016–2022 (latest available)
ACS_YEARS = list(range(2016, 2023))     # 2016–2022 ACS 5-year
BLS_YEARS = list(range(2016, 2025))     # 2016–2024 (BLS is more current)
