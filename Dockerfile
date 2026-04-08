FROM python:3.11-slim

# Create non-root user (HF Spaces requires UID 1000)
RUN useradd -m -u 1000 user

WORKDIR /app

# Install dependencies first for layer caching
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full application
COPY cloud_devops_env/ ./cloud_devops_env/
COPY inference.py ./inference.py

# Copy server files to working directory for uvicorn
COPY cloud_devops_env/server/app.py ./app.py
COPY cloud_devops_env/server/environment.py ./environment.py
COPY cloud_devops_env/server/scenarios.py ./scenarios.py
COPY cloud_devops_env/models.py ./models.py
COPY cloud_devops_env/openenv.yaml ./openenv.yaml

# Set ownership
RUN chown -R user:user /app

USER user

# Expose HF Spaces default port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
