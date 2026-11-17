FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir lxml==5.3.0 cryptography==43.0.1 >/dev/null
COPY server.py ./
EXPOSE 80
CMD ["python", "-u", "server.py"]
