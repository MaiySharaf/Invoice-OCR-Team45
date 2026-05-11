FROM python:3.10-slim

RUN apt update && apt install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

RUN python -m spacy download en_core_web_sm

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY data/ ./data/
COPY models/ ./models/

RUN mkdir -p /app/artifacts/ocr_cache /app/backend/uploads

ENV USE_S3=true
ENV S3_BUCKET=invoice-ocr-uploads-team45
ENV AWS_REGION=eu-north-1

EXPOSE 5000

CMD cd backend && python app.py