FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.0.3 lxml==5.3.0 "PyYAML==6.0.2" >/dev/null
COPY serve.py ./
COPY challenges ./challenges
EXPOSE 80
CMD ["python", "-u", "serve.py"]
