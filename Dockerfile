FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . /app/

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers=4", "--threads=4", "--timeout=120"]