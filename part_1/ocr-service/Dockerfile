FROM python:3.11-slim

WORKDIR /app

# Copy shared dependencies
COPY shared/ /app/shared/

# Copy service files
COPY ocr-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ocr-service/ .

EXPOSE 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]