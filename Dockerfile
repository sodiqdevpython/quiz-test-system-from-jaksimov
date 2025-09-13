# Django uchun Python bazaviy image
FROM python:3.11-slim

# Ishchi papka
WORKDIR /app

# System update va psycopg2 uchun kerakli kutubxonalar
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt ni ko‘chirib o‘rnatish
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Project fayllarini ko‘chirish
COPY . /app/

# Django serverni default ishga tushirish
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
