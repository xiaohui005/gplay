$env:PYTHONUNBUFFERED = "1"
python -m uvicorn src.main:app --reload --port 8008
