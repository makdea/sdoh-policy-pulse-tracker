.PHONY: install setup ingest dbt-seed dbt-run dbt-test dashboard all clean

install:
	pip install -r requirements.txt

setup:
	python setup_db.py

ingest:
	python -m ingestion.run_all

dbt-deps:
	dbt deps

dbt-seed:
	dbt seed --profiles-dir .

dbt-run:
	dbt run --profiles-dir .

dbt-test:
	dbt test --profiles-dir .

dbt-docs:
	dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .

dashboard:
	python dashboard/app.py

# Full pipeline from scratch
all: install setup ingest dbt-deps dbt-seed dbt-run dbt-test

clean:
	dbt clean
	rm -f data/sdoh_pulse.duckdb data/sdoh_pulse.duckdb.wal
