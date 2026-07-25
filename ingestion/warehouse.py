"""
Shared BigQuery load helper for the ingestion scripts.

Each ingestion script builds a pandas DataFrame and hands it to
write_raw_table(), which replaces the table's contents in the `raw` dataset —
equivalent to the old DuckDB DROP TABLE + CREATE TABLE AS pattern.
"""

from google.cloud import bigquery
from google.oauth2 import service_account

from .config import GCP_PROJECT, GCP_KEYFILE_PATH, GCP_LOCATION

import pandas as pd

RAW_DATASET = "raw"

_client = None


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        credentials = service_account.Credentials.from_service_account_file(
            GCP_KEYFILE_PATH
        )
        _client = bigquery.Client(
            project=GCP_PROJECT, credentials=credentials, location=GCP_LOCATION
        )
        _client.create_dataset(
            bigquery.Dataset(f"{GCP_PROJECT}.{RAW_DATASET}"), exists_ok=True
        )
    return _client


def write_raw_table(df: pd.DataFrame, table_name: str) -> int:
    client = _get_client()
    table_id = f"{GCP_PROJECT}.{RAW_DATASET}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        autodetect=True,
    )
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()

    table = client.get_table(table_id)
    return table.num_rows
