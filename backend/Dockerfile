FROM python:3.12-slim

# System deps for playwright, lxml, psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium --with-deps

COPY . .

# Copy start script and make it executable
COPY start.sh .
RUN chmod +x start.sh

# Run both FastAPI and Celery
CMD ["./start.sh"]
