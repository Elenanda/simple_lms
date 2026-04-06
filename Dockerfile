FROM python:3.11-slim

# Mencegah Python menulis file .pyc ke disk
ENV PYTHONDONTWRITEBYTECODE 1
# Memastikan output Python langsung dicetak ke terminal (berguna untuk logging Docker)
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install dependencies terlebih dahulu (memanfaatkan Docker cache)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy sisa source code
COPY . /app/