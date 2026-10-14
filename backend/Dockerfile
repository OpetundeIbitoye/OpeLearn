FROM python:3.12-slim
WORKDIR /srv
RUN pip install --no-cache-dir uv
COPY pyproject.toml .
RUN uv pip install --system -r pyproject.toml --group dev
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libxcb1 libgl1 libglib2.0-0t64 libxext6 libx11-6 libsm6 libice6 \
    && rm -rf /var/lib/apt/lists/*
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
