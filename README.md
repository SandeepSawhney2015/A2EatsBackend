# A2 Eats Backend

FastAPI backend for A2 Eats.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

The API will be available at http://127.0.0.1:8000 with interactive docs at http://127.0.0.1:8000/docs.
