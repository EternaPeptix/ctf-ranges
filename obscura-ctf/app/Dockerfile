FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.0.3 >/dev/null
COPY serve.py common.py ./
COPY challenges ./challenges
EXPOSE 80
CMD ["python", "-u", "serve.py"]
