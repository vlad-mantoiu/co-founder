# AI Co-Founder Backend

FastAPI backend for the AI Technical Co-Founder platform.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest
```
