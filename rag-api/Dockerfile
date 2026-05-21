FROM python:3.12-slim

WORKDIR /app

# Install deps first (layer cache — only invalidated when requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application source
COPY . .

# Knowledge base is mounted at /app/knowledge-base via ConfigMap or hostPath.
# We create the dir so the container starts even without the mount.
RUN mkdir -p /app/knowledge-base

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
