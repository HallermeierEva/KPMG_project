# Deployment Guide

## Production Deployment

### Option 1: Docker

\`\`\`dockerfile
# Dockerfile.part2
FROM python:3.9-slim

WORKDIR /app
COPY part_2/ /app/
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
\`\`\`

Build and run:
\`\`\`bash
docker build -t kpmg-chatbot -f Dockerfile.part2 .
docker run -p 8000:8000 --env-file .env kpmg-chatbot
\`\`\`

### Option 2: Gunicorn (Production Server)

\`\`\`bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker part_2.main:app
\`\`\`

### Environment Variables in Production

Use Azure Key Vault or similar:
\`\`\`bash
export AZURE_OPENAI_KEY=$(az keyvault secret show --vault-name myvault --name openai-key --query value -o tsv)
\`\`\`

### Monitoring

Add Azure Application Insights:
\`\`\`python
from opencensus.ext.azure.log_exporter import AzureLogHandler
logger.addHandler(AzureLogHandler(connection_string='...'))
\`\`\`