FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY backend /app/backend
COPY alembic.ini /app/alembic.ini
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["sh", "-c", "alembic -c /app/alembic.ini upgrade head && uvicorn backend.app.main:app --host 0.0.0.0"]
