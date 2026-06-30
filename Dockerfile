FROM python:3.12-slim

WORKDIR /app

# Sistem bağımlılıklarını kur (psycopg2, vb. için gerekebilir)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Gereksinimleri kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# Portu dışarı aç
EXPOSE 8000

# Geliştirme sunucusunu başlat (production için gunicorn önerilir)
CMD ["python", "backend/manage.py", "runserver", "0.0.0.0:8000"]
