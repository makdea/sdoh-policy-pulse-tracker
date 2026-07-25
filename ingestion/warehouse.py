"""
Shared BigQuery load helper for the ingestion scripts.

Each ingestion script builds a pandas DataFrame and hands it to
write_raw_table(), which replaces the table's contents in the `raw` dataset —
equivalent to the old DuckDB DROP TABLE + CREATE TABLE AS pattern.

Auth: this org blocks service-account key creation
(iam.disableServiceAccountKeyCreation), so there's no keyfile. The client
picks up Application Default Credentials instead — run
`gcloud auth application-default login` once before running ingestion.
"""

from google.cloud import bigquery

from .config import GCP_PROJECT, GCP_LOCATION

import pandas as pd

RAW_DATASET = "raw"

_client = None


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=GCP_PROJECT, location=GCP_LOCATION)
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
