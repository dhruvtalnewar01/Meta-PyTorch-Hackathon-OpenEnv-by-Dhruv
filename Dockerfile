FROM python:3.11-slim
LABEL version="2.1.1" description="CloudDevOps-Env OpenEnv SRE Simulator"

# Create non-root user (HF Spaces requires UID 1000)
RUN useradd -m -u 1000 user

WORKDIR /app

# Install dependencies first for layer caching
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full application
COPY . /app

# The entrypoint expects module to be found
ENV PYTHONPATH="/app"

# Set ownership
RUN chown -R user:user /app

USER user

# Expose HF Spaces default port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
