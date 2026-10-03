FROM python:3.11-slim

WORKDIR /app

# Install backend requirements (litellm, sqlalchemy, etc. needed by scorers)
COPY backend/requirements.txt backend-req.txt
RUN pip install --no-cache-dir -r backend-req.txt

# Install worker-specific requirements
COPY worker/requirements.txt worker-req.txt
RUN pip install --no-cache-dir -r worker-req.txt

# Copy scorer code from backend (scorers only import from each other + litellm)
COPY backend/app/__init__.py ./app/__init__.py
COPY backend/app/scorers ./app/scorers

# Copy worker files
COPY worker/celery_app.py .
COPY worker/tasks ./tasks

CMD ["celery", "-A", "celery_app", "worker", "--loglevel=info", "--concurrency=4"]
