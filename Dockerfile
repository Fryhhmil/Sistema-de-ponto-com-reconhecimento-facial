FROM python:3.10-slim

# Build deps for dlib / face_recognition
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        libopenblas-dev \
        liblapack-dev \
        libx11-dev \
        libgtk-3-dev \
        libboost-python-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# instance/ lives outside the image so data survives container restarts
VOLUME ["/app/instance"]

ENV FLASK_APP=run.py \
    FLASK_ENV=production \
    SECRET_KEY=troque-esta-chave-em-producao

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
