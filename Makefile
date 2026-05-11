.PHONY: install api ui ingest check

install:
	python -m pip install -r requirements.txt

api:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

ui:
	streamlit run streamlit_app/Home.py --server.port 8501 --server.address 0.0.0.0

ingest:
	python -m app.ingest_markdown --knowledge-dir ./knowledge --rebuild

check:
	python scripts/check_connections.py
