FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
COPY seed ./seed

EXPOSE 8000

# Apply migrations and sync boss reference data on every start; both are safe
# to repeat. V1 attempt history is imported separately, once, by hand.
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.import_v1_data && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
