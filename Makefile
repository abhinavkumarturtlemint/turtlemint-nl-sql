VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

.PHONY: install seed backend frontend test

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

seed:
	$(PY) -m app.data.seed

backend:
	$(VENV)/bin/uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --reload

frontend:
	$(VENV)/bin/streamlit run app/frontend/app.py

test:
	$(PY) -m pytest -q
