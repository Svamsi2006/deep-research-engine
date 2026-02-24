FROM python:3.12-slim

WORKDIR /app

# System deps for Playwright & Scrapy
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Install Playwright browsers
RUN pip install playwright && playwright install --with-deps chromium

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
