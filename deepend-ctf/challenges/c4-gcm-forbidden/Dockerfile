FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.0.3 cryptography==43.0.1 >/dev/null
COPY app.py ./
EXPOSE 80
CMD ["python", "-u", "app.py"]
