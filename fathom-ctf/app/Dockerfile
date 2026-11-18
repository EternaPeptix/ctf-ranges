FROM python:3.12-slim

RUN pip install --no-cache-dir flask==3.0.3

WORKDIR /app
COPY serve.py /app/serve.py

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 80
CMD ["python", "/app/serve.py"]
