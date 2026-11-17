FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.0.3 >/dev/null
COPY app.py ./
COPY backup/ /backup/
EXPOSE 80
CMD ["python", "-u", "app.py"]
